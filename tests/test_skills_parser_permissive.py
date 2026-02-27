from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.skills.skillmd_parser import SkillMdParser


class SkillParserPermissiveTests(unittest.TestCase):
    def test_invalid_frontmatter_falls_back_with_warning(self) -> None:
        parser = SkillMdParser(permissive=True)
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "skills" / "broken-skill"
            skill_dir.mkdir(parents=True, exist_ok=True)
            path = skill_dir / "SKILL.md"
            path.write_text("This has no frontmatter and should still load.\n", encoding="utf-8")
            descriptor, warnings = parser.parse_file_with_diagnostics(path, include_body=False, permissive=True)
            self.assertIsNotNone(descriptor)
            assert descriptor is not None
            self.assertEqual(descriptor.skill_id, "broken-skill")
            self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
