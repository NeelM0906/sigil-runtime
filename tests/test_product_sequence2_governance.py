from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.runtime.bridge import RuntimeBridge
from bomba_sr.runtime.config import RuntimeConfig


class ProductSequence2GovernanceTests(unittest.TestCase):
    def test_code_tool_requires_approval_under_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "main.py").write_text("def demo():\n    return 1\n", encoding="utf-8")

            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home))
            tenant = "tenant-govern"

            response = bridge.invoke_code_tool(
                tenant_id=tenant,
                tool_name="rename_symbol",
                arguments={"old_name": "demo", "new_name": "demo2", "scope": ["."]},
                workspace_root=str(workspace),
                session_id="s1",
                turn_id="t1",
                confidence=0.1,
            )
            self.assertEqual(response["status"], "approval_required")
            approval_id = response["approval_id"]

            pending = bridge.list_pending_approvals(tenant_id=tenant, workspace_root=str(workspace))
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["approval_id"], approval_id)

            decided = bridge.decide_approval(
                tenant_id=tenant,
                approval_id=approval_id,
                approved=True,
                decided_by="tester",
                workspace_root=str(workspace),
            )
            self.assertEqual(decided["status"], "approved")


if __name__ == "__main__":
    unittest.main()
