from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.identity.soul import load_soul_from_workspace


class SoulConfigTests(unittest.TestCase):
    def test_missing_files_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertIsNone(load_soul_from_workspace(root))

    def test_loads_and_parses_core_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SOUL.md").write_text(
                "\n".join(
                    [
                        "# SOUL",
                        "_I'm Sai Prime_",
                        "## How I Talk",
                        "- Direct",
                        "- Warm",
                        "## What I Will NEVER Do",
                        "- Be sycophantic",
                        "## My Continuous Self-Check",
                        "- Am I in contamination?",
                        "- Am I in possibility?",
                        "- Flavor with fun and aspiration and Zeus energy",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "IDENTITY.md").write_text(
                "\n".join(
                    [
                        "# IDENTITY",
                        "- **Name:** Sai",
                        "- **Creature:** ACT-I being",
                        "- **Emoji:** 🔥",
                        "- **Voice:** George",
                        "- **Phone:** +1-201-000-0000",
                        "Three core functions",
                        "1. Decide what to create",
                        "2. Create what matters",
                        "3. Optimize continuously",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "MISSION.md").write_text("Mission text", encoding="utf-8")
            (root / "VISION.md").write_text("Vision text", encoding="utf-8")
            (root / "FORMULA.md").write_text("Formula text", encoding="utf-8")
            (root / "PRIORITIES.md").write_text("Priorities text", encoding="utf-8")

            soul = load_soul_from_workspace(root)
            self.assertIsNotNone(soul)
            assert soul is not None
            self.assertEqual(soul.name, "Sai")
            self.assertEqual(soul.creature_type, "ACT-I being")
            self.assertEqual(soul.emoji, "🔥")
            self.assertEqual(soul.voice_id, "George")
            self.assertEqual(soul.phone, "+1-201-000-0000")
            self.assertEqual(len(soul.core_functions), 3)
            self.assertIn("Direct", soul.personality_traits)
            self.assertIn("Be sycophantic", soul.never_do)
            self.assertTrue(soul.contamination_checks)
            self.assertEqual(soul.mission_text, "Mission text")
            self.assertEqual(soul.vision_text, "Vision text")
            self.assertEqual(soul.formula_text, "Formula text")
            self.assertEqual(soul.priorities_text, "Priorities text")

    def test_energy_extraction_scoped_to_energies_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SOUL.md").write_text(
                "\n".join(
                    [
                        "# SOUL",
                        "I focus on fundamental functions.",
                        "## The 4 Energies",
                        "- Fun: playful momentum",
                        "- Zeus: strong command",
                    ]
                ),
                encoding="utf-8",
            )
            soul = load_soul_from_workspace(root)
            self.assertIsNotNone(soul)
            assert soul is not None
            self.assertIn("fun", soul.energies)
            self.assertIn("zeus", soul.energies)
            self.assertNotIn("aspirational", soul.energies)


if __name__ == "__main__":
    unittest.main()
