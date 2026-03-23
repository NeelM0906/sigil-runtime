from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolDefinition, ToolExecutor, truncate_output
from bomba_sr.tools.builtin_exec import builtin_exec_tools


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


class OuroborosTruncationTests(unittest.TestCase):
    def test_truncate_output_preserves_head_and_tail(self) -> None:
        payload = {"text": "a" * 1000, "other": "ok"}
        truncated = truncate_output(payload, max_chars=100)
        self.assertIn("chars truncated", truncated["text"])
        self.assertTrue(truncated["text"].startswith("a" * 50))
        self.assertTrue(truncated["text"].endswith("a" * 50))
        self.assertEqual(truncated["other"], "ok")

    def test_tool_executor_truncates_large_result_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-trunc")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline, tool_result_max_chars=120)
            executor.register(
                ToolDefinition(
                    name="huge_read",
                    description="returns long string",
                    parameters={"type": "object", "properties": {}, "additionalProperties": False},
                    risk_level="low",
                    action_type="read",
                    execute=lambda _args, _ctx: {"blob": "z" * 500},
                )
            )
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-trunc"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-trunc",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            result = executor.execute("huge_read", {}, context=context, policy=policy, confidence=1.0)
            self.assertEqual(result.status, "executed")
            self.assertIn("chars truncated", result.output["blob"])

    def test_shell_output_has_own_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-shell-trunc")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline, tool_result_max_chars=15000)
            executor.register_many(builtin_exec_tools(default_max_output_chars=200))
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-shell-trunc"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-shell-trunc",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            result = executor.execute(
                "exec",
                {"command": "python3 -c \"print('a'*3000)\""},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(result.status, "executed")
            self.assertIn("chars truncated", result.output["stdout"])


if __name__ == "__main__":
    unittest.main()
