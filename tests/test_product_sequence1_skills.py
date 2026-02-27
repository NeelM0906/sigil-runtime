from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.runtime.bridge import RuntimeBridge
from bomba_sr.runtime.config import RuntimeConfig


class ProductSequence1SkillsTests(unittest.TestCase):
    def test_register_and_execute_template_skill(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)

            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home))
            tenant = "tenant-skill"

            manifest = {
                "skill_id": "daily_summary",
                "version": "1.0.0",
                "name": "Daily Summary",
                "description": "Summarize current project context",
                "entrypoint": {
                    "type": "template",
                    "template": "Summary for project {{project_id}} and task {{task_id}}",
                },
                "intent_tags": ["summary"],
                "inputs": {"project_id": {"type": "string"}, "task_id": {"type": "string"}},
                "outputs": {"text": {"type": "string"}},
                "tools_required": [],
                "risk_level": "low",
                "default_enabled": True,
            }

            reg = bridge.register_skill(tenant_id=tenant, manifest=manifest, status="active", workspace_root=str(workspace))
            self.assertEqual(reg["skill_id"], "daily_summary")

            skills = bridge.list_skills(tenant_id=tenant, workspace_root=str(workspace))
            self.assertTrue(any(s["skill_id"] == "daily_summary" for s in skills))

            result = bridge.execute_skill(
                tenant_id=tenant,
                skill_id="daily_summary",
                inputs={"project_id": "p1", "task_id": "t1"},
                workspace_root=str(workspace),
                session_id=str(uuid.uuid4()),
                turn_id=str(uuid.uuid4()),
            )
            self.assertEqual(result["status"], "completed")
            self.assertIn("Summary for project p1", result["output"]["text"])


if __name__ == "__main__":
    unittest.main()
