from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from bomba_sr.runtime.tenancy import TenantRegistry
from bomba_sr.storage.db import RuntimeDB


def _load_import_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "import_sai_memory.py"
    spec = importlib.util.spec_from_file_location("import_sai_memory", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load import_sai_memory module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ImportSaiMemoryTests(unittest.TestCase):
    def test_import_workspace_memory_writes_expected_tables(self) -> None:
        module = _load_import_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "workspace"
            memory = source / "memory"
            memory.mkdir(parents=True, exist_ok=True)

            (memory / "2026-02-22.md").write_text("# Daily log\nnotes", encoding="utf-8")
            (memory / "call-2026-02-22-abc123.md").write_text(
                "\n".join(
                    [
                        "# Voice Call Transcript",
                        "- **Date:** 2/22/2026, 1:20:42 PM",
                        "- **Duration:** 25s",
                        "- **Turns:** 11",
                    ]
                ),
                encoding="utf-8",
            )
            (memory / "heart-of-influence-research.md").write_text("semantic text", encoding="utf-8")
            (source / "MEMORY.md").write_text("memory index", encoding="utf-8")
            (source / "FORMULA.md").write_text(
                "\n".join(
                    [
                        "### Self Mastery (7) — The 7 Liberators / Destroyers",
                        "| # | Liberator | Destroyer | Notes |",
                        "|---|---|---|---|",
                        "| 1 | L | D | N |",
                        "#### The 4 Steps of Integrity-Based Human Influence",
                        "1. Step one",
                        "#### The 12 Indispensable Elements",
                        "1. Element one",
                        "#### The 4 Energies",
                        "1. Fun",
                        "### Process Mastery (4)",
                        "1. Modeling",
                        "### The 7 Levers of Marketing & Sales Process Mastery (8 including 0.5)",
                        "- **Lever 0.5: Shared Experiences** — Shared context",
                        "- Lever 1: Ecosystem Merging",
                        "- Levers 2-7: TBD",
                    ]
                ),
                encoding="utf-8",
            )

            runtime_home = root / "runtime-home"
            stats = module.import_workspace_memory(
                source_workspace=source,
                tenant_id="tenant-prime",
                user_id="sai-prime",
                dry_run=False,
                runtime_home=runtime_home,
            )

            self.assertGreaterEqual(stats.daily_logs, 1)
            self.assertGreaterEqual(stats.call_transcripts, 1)
            self.assertGreaterEqual(stats.memory_index, 1)
            self.assertGreaterEqual(stats.semantic_memories, 1)
            self.assertGreaterEqual(stats.procedural_memories, 1)

            tenant_ctx = TenantRegistry(runtime_home).ensure_tenant("tenant-prime")
            self.assertTrue(tenant_ctx.db_path.resolve().is_relative_to(runtime_home.resolve()))
            db = RuntimeDB(tenant_ctx.db_path)
            note_count = db.execute("SELECT COUNT(*) AS c FROM markdown_notes").fetchone()["c"]
            semantic_count = db.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
            procedural_count = db.execute("SELECT COUNT(*) AS c FROM procedural_memories").fetchone()["c"]
            self.assertGreaterEqual(int(note_count), 3)
            self.assertGreaterEqual(int(semantic_count), 1)
            self.assertGreaterEqual(int(procedural_count), 1)
            db.close()

    def test_semantic_import_is_idempotent_for_whitespace_changes(self) -> None:
        module = _load_import_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "workspace"
            memory = source / "memory"
            memory.mkdir(parents=True, exist_ok=True)

            semantic_path = memory / "heart-of-influence-research.md"
            semantic_path.write_text("line one\nline two", encoding="utf-8")
            (source / "FORMULA.md").write_text("", encoding="utf-8")

            runtime_home = root / "runtime-home"

            class _Cfg:
                def __init__(self):
                    self.runtime_home = runtime_home

            module.import_workspace_memory(
                source_workspace=source,
                tenant_id="tenant-prime",
                user_id="sai-prime",
                dry_run=False,
                runtime_home=runtime_home,
            )
            semantic_path.write_text("line one   \n\nline two  ", encoding="utf-8")
            module.import_workspace_memory(
                source_workspace=source,
                tenant_id="tenant-prime",
                user_id="sai-prime",
                dry_run=False,
                runtime_home=runtime_home,
            )

            tenant_ctx = TenantRegistry(runtime_home).ensure_tenant("tenant-prime")
            db = RuntimeDB(tenant_ctx.db_path)
            row = db.execute(
                """
                SELECT COUNT(*) AS active_count
                FROM memories
                WHERE user_id = ? AND memory_key = ? AND active = 1
                """,
                ("sai-prime", "import::workspace::heart-of-influence-research"),
            ).fetchone()
            archive = db.execute(
                """
                SELECT COUNT(*) AS archive_count
                FROM memory_archive
                WHERE user_id = ? AND memory_key = ?
                """,
                ("sai-prime", "import::workspace::heart-of-influence-research"),
            ).fetchone()
            self.assertEqual(int(row["active_count"]), 1)
            self.assertEqual(int(archive["archive_count"]), 0)
            db.close()


    def test_parse_levers_produces_distinct_content_for_all_levers(self) -> None:
        """Regression: levers 3-7 must NOT all contain 'Lever 0.5: Shared Experiences'."""
        module = _load_import_module()
        formula_text = "\n".join([
            "### The 7 Levers of Marketing & Sales Process Mastery (8 including 0.5)",
            "- **Lever 0.5: Shared Experiences** — Building common ground through events",
            "- Lever 1: Ecosystem Merging (O's and B's) — Strategic network merging",
            "- Levers 2-7: Speaking Engagements, Meetings, Sales, Disposable Income, Contribution, Fun & Magic",
            "### Another Section",
        ])
        levers = module._parse_levers(formula_text)
        lever_dict = dict(levers)

        # All 9 keys should be present (0.5, 1, 2, 3, 4, 5, 6, 7)
        self.assertIn("formula_lever_0_5", lever_dict)
        self.assertIn("formula_lever_1", lever_dict)
        for idx in range(2, 8):
            self.assertIn(f"formula_lever_{idx}", lever_dict, f"Lever {idx} missing")

        # Lever 0.5 should reference Shared Experiences
        self.assertIn("Shared Experiences", lever_dict["formula_lever_0_5"])

        # Lever 1 should reference Ecosystem Merging
        self.assertIn("Ecosystem Merging", lever_dict["formula_lever_1"])

        # Levers 2-7 should NOT contain "Lever 0.5" or "Shared Experiences"
        for idx in range(2, 8):
            key = f"formula_lever_{idx}"
            self.assertNotIn("Lever 0.5", lever_dict[key], f"{key} wrongly contains Lever 0.5 content")
            self.assertNotIn("Shared Experiences", lever_dict[key], f"{key} wrongly contains Shared Experiences")

        # All lever values should be distinct (no duplicates)
        values = list(lever_dict.values())
        self.assertEqual(len(values), len(set(values)), "Lever values are not all distinct")

        # Levers 2-7 should not have redundant "Levers 2-7:" prefix
        for idx in range(2, 8):
            self.assertNotIn("Levers 2-7:", lever_dict[f"formula_lever_{idx}"])


if __name__ == "__main__":
    unittest.main()
