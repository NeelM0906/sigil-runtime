from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.memory.hybrid import HybridMemoryStore
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_approvals import builtin_approval_tools


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


class UnifiedApprovalsTests(unittest.TestCase):
    def test_list_and_decide_tool_and_learning_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-a")
            memory = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)

            # Seed one tool approval.
            tool_decision = governance.evaluate(
                tenant_id="tenant-a",
                action_type="write",
                risk_class="high",
                confidence=0.1,
                payload={"tool_name": "rename_symbol"},
                session_id="s1",
                turn_id="t1",
            )
            self.assertTrue(tool_decision.requires_approval)

            # Seed one learning approval.
            learning = memory.learn_semantic(
                tenant_id="tenant-a",
                user_id="user-a",
                memory_key="pref.editor",
                content="User prefers vim",
                confidence=0.1,
                evidence_refs=[],
                reason="test",
            )
            self.assertEqual(learning.status, "pending")

            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_approval_tools(governance, memory))
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-a"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-a",
                session_id="s1",
                turn_id="t1",
                user_id="user-a",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )

            listed = executor.execute(
                "list_approvals",
                {"type": "all"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(listed.status, "executed")
            ids = {item["id"] for item in listed.output["approvals"]}
            self.assertTrue(any(x.startswith("tool:") for x in ids))
            self.assertTrue(any(x.startswith("learning:") for x in ids))

            decide_learning = executor.execute(
                "decide_approval",
                {"approval_id": f"learning:{learning.update_id}", "approved": True},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(decide_learning.status, "executed")
            self.assertEqual(decide_learning.output["kind"], "learning")

            decide_tool = executor.execute(
                "decide_approval",
                {"approval_id": f"tool:{tool_decision.approval_id}", "approved": True},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(decide_tool.status, "executed")
            self.assertEqual(decide_tool.output["kind"], "tool")


if __name__ == "__main__":
    unittest.main()
