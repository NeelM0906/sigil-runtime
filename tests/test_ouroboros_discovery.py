from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolDefinition, ToolExecutor
from bomba_sr.tools.builtin_discovery import builtin_discovery_tools


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate != root.resolve() and root.resolve() not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class OuroborosDiscoveryTests(unittest.TestCase):
    def test_enable_tools_expands_groups_and_respects_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            state = SimpleNamespace(active_tool_overrides=set(), denied_tools={"exec"})
            context = ToolContext(
                tenant_id="tenant-disc",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
                loop_state_ref=state,
            )
            tool = builtin_discovery_tools()[0]
            out = tool.execute({"groups": ["group:runtime", "group:missing"], "reason": "need more tools"}, context)
            self.assertIn("process", out["enabled"])
            self.assertIn("exec", out["denied"])
            self.assertIn("group:missing", out["denied"])
            self.assertIn("process", state.active_tool_overrides)

    def test_available_tool_schemas_with_overrides_honors_deny(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-disc")
            pipeline = PolicyPipeline(governance, global_deny=("exec_extra",))
            executor = ToolExecutor(governance, pipeline)
            executor.register(
                ToolDefinition(
                    name="read_extra",
                    description="read",
                    parameters={"type": "object", "properties": {}, "additionalProperties": True},
                    risk_level="low",
                    action_type="read",
                    execute=lambda _args, _ctx: {"ok": True},
                )
            )
            executor.register(
                ToolDefinition(
                    name="exec_extra",
                    description="exec",
                    parameters={"type": "object", "properties": {}, "additionalProperties": True},
                    risk_level="medium",
                    action_type="execute",
                    execute=lambda _args, _ctx: {"ok": True},
                )
            )
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-disc"),
                available_tools=executor.known_tool_names(),
            )
            schemas = executor.available_tool_schemas_with_overrides(
                policy=policy,
                overrides={"read_extra", "exec_extra"},
                format="openai",
            )
            names = [item["function"]["name"] for item in schemas]
            self.assertIn("read_extra", names)
            self.assertNotIn("exec_extra", names)


if __name__ == "__main__":
    unittest.main()
