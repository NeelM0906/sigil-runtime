from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_skills import builtin_skill_tools


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


class SkillToolsTests(unittest.TestCase):
    def test_create_and_update_skill_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            (root / "skills").mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            registry = SkillRegistry(db)
            loader = SkillLoader(
                skill_roots=[root / "skills"],
                eligibility=EligibilityEngine(),
                parser=SkillMdParser(),
            )
            loader.scan()

            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-skill-tools")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_skill_tools(loader, registry))
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-skill-tools"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-skill-tools",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )

            created = executor.execute(
                "skill_create",
                {
                    "name": "review-helper",
                    "description": "Review pull requests quickly",
                    "body": "Run through changed files and summarize risks.",
                },
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(created.status, "executed")
            skill_file = root / "skills" / "review-helper" / "SKILL.md"
            self.assertTrue(skill_file.exists())
            self.assertIn("Review pull requests quickly", skill_file.read_text(encoding="utf-8"))

            listed = registry.list_skills("tenant-skill-tools")
            self.assertTrue(any(s.skill_id == "review-helper" and s.source == "filesystem" for s in listed))

            updated = executor.execute(
                "skill_update",
                {
                    "skill_id": "review-helper",
                    "description": "Review code and propose safer refactors",
                },
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(updated.status, "executed")
            self.assertIn("safer refactors", skill_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
