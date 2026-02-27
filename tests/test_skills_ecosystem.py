from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.skills.ecosystem import SOURCE_ANTHROPIC, SOURCE_CLAWHUB, SkillEcosystemService
from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.storage.db import RuntimeDB


def _fake_fetch(url: str) -> bytes:
    if "repos/openclaw/clawhub/git/trees/main" in url:
        return json.dumps(
            {"tree": [{"path": "skills/daily-brief/SKILL.md"}]}
        ).encode("utf-8")
    if "repos/anthropics/skills/git/trees/main" in url:
        return json.dumps(
            {"tree": [{"path": "research/SKILL.md"}]}
        ).encode("utf-8")
    if "daily-brief/SKILL.md" in url:
        return (
            "---\n"
            "name: daily-brief\n"
            "description: Create a concise daily brief\n"
            "---\n"
            "Summarize the user's day.\n"
        ).encode("utf-8")
    if "research/SKILL.md" in url:
        return (
            "---\n"
            "name: research\n"
            "description: research helper\n"
            "---\n"
            "Do careful research.\n"
        ).encode("utf-8")
    raise AssertionError(f"unexpected url: {url}")


class SkillEcosystemTests(unittest.TestCase):
    def test_catalog_and_approval_install_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = RuntimeDB(root / "runtime.sqlite3")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-a")
            registry = SkillRegistry(db)
            parser = SkillMdParser(permissive=True)
            loader = SkillLoader([root / "skills"], EligibilityEngine(), parser)

            svc = SkillEcosystemService(
                db=db,
                registry=registry,
                loader=loader,
                parser=parser,
                governance=governance,
                enabled_sources=(SOURCE_CLAWHUB, SOURCE_ANTHROPIC),
                telemetry_enabled=True,
                fetcher=_fake_fetch,
            )
            catalog = svc.list_catalog_skills(limit=20)
            self.assertEqual({item.source for item in catalog}, {SOURCE_CLAWHUB, SOURCE_ANTHROPIC})

            req = svc.create_install_request(
                tenant_id="tenant-a",
                user_id="user-a",
                source=SOURCE_CLAWHUB,
                skill_id="daily-brief",
                workspace_root=str(root),
                session_id="s1",
                turn_id="t1",
            )
            self.assertEqual(req.status, "pending_approval")
            self.assertIsNotNone(req.approval_id)

            governance.decide_approval("tenant-a", req.approval_id or "", approved=True, decided_by="user")
            applied = svc.execute_install("tenant-a", req.request_id, workspace_root=str(root))
            self.assertTrue(applied["installed"])
            installed = root / "skills" / "daily-brief" / "SKILL.md"
            self.assertTrue(installed.exists())

            skills = registry.list_skills("tenant-a")
            self.assertTrue(any(s.skill_id == "daily-brief" for s in skills))

    def test_trust_override_blocks_install(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = RuntimeDB(root / "runtime.sqlite3")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-b")
            registry = SkillRegistry(db)
            parser = SkillMdParser(permissive=True)
            loader = SkillLoader([root / "skills"], EligibilityEngine(), parser)
            svc = SkillEcosystemService(
                db=db,
                registry=registry,
                loader=loader,
                parser=parser,
                governance=governance,
                fetcher=_fake_fetch,
            )

            svc.set_trust_override("tenant-b", SOURCE_CLAWHUB, "blocked")
            with self.assertRaises(ValueError):
                svc.create_install_request(
                    tenant_id="tenant-b",
                    user_id="user-b",
                    source=SOURCE_CLAWHUB,
                    skill_id="daily-brief",
                    workspace_root=str(root),
                    session_id="s1",
                    turn_id="t1",
                )


if __name__ == "__main__":
    unittest.main()
