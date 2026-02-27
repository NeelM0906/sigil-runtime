from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.skills.descriptor import descriptor_from_manifest
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.storage.db import RuntimeDB


class SkillDescriptorTests(unittest.TestCase):
    def test_descriptor_from_manifest_normalizes_fields(self) -> None:
        manifest = {
            "skill_id": "review",
            "version": "2.0.0",
            "name": "review",
            "description": "Run a review",
            "intent_tags": ["review", "code"],
            "tools_required": ["read", "grep"],
            "risk_level": "high",
            "default_enabled": False,
            "user_invocable": True,
            "disable_model_invocation": False,
        }
        descriptor = descriptor_from_manifest(manifest)
        self.assertEqual(descriptor.skill_id, "review")
        self.assertEqual(descriptor.intent_tags, ("review", "code"))
        self.assertEqual(descriptor.tools_required, ("read", "grep"))
        self.assertEqual(descriptor.risk_level, "high")
        self.assertFalse(descriptor.default_enabled)

    def test_register_from_descriptor_persists_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(Path(td) / "runtime.db")
            registry = SkillRegistry(db)
            descriptor = descriptor_from_manifest(
                {
                    "skill_id": "doc_skill",
                    "version": "1.0.0",
                    "name": "doc_skill",
                    "description": "Doc-only skill",
                    "intent_tags": ["doc"],
                    "tools_required": [],
                    "risk_level": "low",
                    "default_enabled": True,
                    "user_invocable": True,
                    "disable_model_invocation": False,
                },
                source="filesystem",
                source_path="/tmp/skills/doc_skill/SKILL.md",
            )
            record = registry.register_from_descriptor("tenant-a", descriptor, status="active")
            self.assertEqual(record.skill_id, "doc_skill")
            self.assertEqual(record.source, "filesystem")
            self.assertEqual(record.source_path, "/tmp/skills/doc_skill/SKILL.md")
            listed = registry.list_skills("tenant-a", status="active")
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].source, "filesystem")


if __name__ == "__main__":
    unittest.main()
