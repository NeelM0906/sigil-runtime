from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class ProductSequence3ProjectsTests(unittest.TestCase):
    def test_project_task_linked_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "mod.py").write_text("def fn():\n    return 'ok'\n", encoding="utf-8")

            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home), provider=StaticEchoProvider())
            tenant = "tenant-proj"

            project = bridge.create_project(
                tenant_id=tenant,
                name="Proj A",
                workspace_root=str(workspace),
                runtime_workspace_root=str(workspace),
            )
            task = bridge.create_task(
                tenant_id=tenant,
                project_id=project["project_id"],
                title="Task A",
                workspace_root=str(workspace),
            )

            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant,
                    session_id=str(uuid.uuid4()),
                    user_id="user-a",
                    user_message="create a markdown status report for this task",
                    workspace_root=str(workspace),
                    profile=TurnProfile.TASK_EXECUTION,
                    project_id=project["project_id"],
                    task_id=task["task_id"],
                )
            )

            self.assertEqual(result["turn"]["project_id"], project["project_id"])
            self.assertEqual(result["turn"]["task_id"], task["task_id"])
            self.assertTrue(result["artifacts"])
            self.assertEqual(result["artifacts"][0]["project_id"], project["project_id"])
            self.assertEqual(result["artifacts"][0]["task_id"], task["task_id"])


if __name__ == "__main__":
    unittest.main()
