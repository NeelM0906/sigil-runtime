from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolDefinition, ToolExecutor


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_real = root.resolve()
        if candidate != root_real and root_real not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class PolicyGovernanceIntegrationTests(unittest.TestCase):
    def test_policy_then_governance_decision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-z")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register(
                ToolDefinition(
                    name="write",
                    description="write",
                    parameters={"type": "object", "properties": {}, "additionalProperties": True},
                    risk_level="medium",
                    action_type="write",
                    execute=lambda _args, _ctx: {"ok": True},
                )
            )

            context = ToolContext(
                tenant_id="tenant-z",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )

            minimal_policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.MINIMAL, tenant_id="tenant-z"),
                available_tools=executor.known_tool_names(),
            )
            denied = executor.execute("write", {}, context=context, policy=minimal_policy, confidence=1.0)
            self.assertEqual(denied.status, "denied")

            full_policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-z"),
                available_tools=executor.known_tool_names(),
            )
            needs_approval = executor.execute("write", {}, context=context, policy=full_policy, confidence=0.1)
            self.assertEqual(needs_approval.status, "approval_required")
            self.assertIn("approval_id", needs_approval.output)


if __name__ == "__main__":
    unittest.main()
