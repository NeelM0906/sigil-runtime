from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.skillmd_parser import SkillMdParser


def _write_skill(path: Path, name: str, description: str, body: str, metadata: str | None = None) -> None:
    skill_dir = path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if metadata is not None:
        lines.append(f"metadata: '{metadata}'")
    lines.extend(["---", body])
    (skill_dir / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")


class SkillLoaderTests(unittest.TestCase):
    def test_scan_precedence_and_lazy_body_loading(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            high = td_path / "high"
            low = td_path / "low"
            high.mkdir(parents=True, exist_ok=True)
            low.mkdir(parents=True, exist_ok=True)

            _write_skill(low, "summarize", "Low precedence description", "low body")
            _write_skill(high, "summarize", "High precedence description", "high body")

            loader = SkillLoader(
                skill_roots=[high, low],
                eligibility=EligibilityEngine(),
                parser=SkillMdParser(),
            )
            snapshot = loader.scan()
            self.assertIn("summarize", snapshot)
            descriptor = snapshot["summarize"]
            self.assertEqual(descriptor.description, "High precedence description")
            self.assertFalse(descriptor._body_loaded)
            self.assertEqual(descriptor.body_text, "")

            body = loader.load_skill_body("summarize")
            self.assertIn("high body", body)
            loaded = loader.snapshot()["summarize"]
            self.assertTrue(loaded._body_loaded)

    def test_scan_filters_ineligible_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(
                root,
                "needs_missing_bin",
                "Requires missing binary",
                "body",
                metadata='{"sigil":{"requires":{"bins":["definitely_missing_bin"]}}}',
            )
            loader = SkillLoader(
                skill_roots=[root],
                eligibility=EligibilityEngine(),
                parser=SkillMdParser(),
            )
            snapshot = loader.scan()
            self.assertEqual(snapshot, {})


if __name__ == "__main__":
    unittest.main()
