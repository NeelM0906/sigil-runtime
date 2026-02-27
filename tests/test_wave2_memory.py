from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from bomba_sr.memory.consolidation import MemoryCandidate, MemoryConsolidator
from bomba_sr.storage.db import RuntimeDB


class MemoryConsolidatorTests(unittest.TestCase):
    def test_contradiction_archives_old_memory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            consolidator = MemoryConsolidator(db)
            user = str(uuid.uuid4())

            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="preferred_editor",
                    content="User prefers Vim",
                )
            )
            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="preferred_editor",
                    content="User now prefers Neovim",
                )
            )

            self.assertEqual(consolidator.archive_count(user, "preferred_editor"), 1)
            results = consolidator.retrieve(user_id=user, query="preferred editor")
            self.assertTrue(results)
            self.assertIn("Neovim", results[0].content)

    def test_temporal_rerank_prefers_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            consolidator = MemoryConsolidator(db)
            user = str(uuid.uuid4())

            old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            new_ts = datetime.now(timezone.utc).isoformat()

            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="deploy_note_old",
                    content="Use blue deploy pipeline",
                    recency_ts=old_ts,
                )
            )
            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="deploy_note_new",
                    content="Use blue deploy pipeline",
                    recency_ts=new_ts,
                )
            )

            results = consolidator.retrieve(user_id=user, query="blue deploy pipeline", limit=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].key, "deploy_note_new")
            self.assertGreater(results[0].score, results[1].score)

    def test_noise_filter_excludes_meta_memory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            consolidator = MemoryConsolidator(db)
            user = str(uuid.uuid4())

            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="meta_noise",
                    content="Do you remember what I said yesterday?",
                )
            )
            consolidator.upsert(
                MemoryCandidate(
                    user_id=user,
                    key="substantive",
                    content="Sourdough recipe uses 72-hour cold ferment",
                )
            )

            results = consolidator.retrieve(user_id=user, query="sourdough recipe")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].key, "substantive")

    def test_procedural_memory_learn_and_recall(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            consolidator = MemoryConsolidator(db)
            user = str(uuid.uuid4())

            consolidator.learn_procedural(
                user_id=user,
                strategy_key="search_then_patch",
                content="Use glob then read then apply_patch for multi-file edits.",
                success=True,
            )
            consolidator.learn_procedural(
                user_id=user,
                strategy_key="search_then_patch",
                content="Use glob then read then apply_patch for multi-file edits.",
                success=True,
            )
            consolidator.learn_procedural(
                user_id=user,
                strategy_key="blind_patch",
                content="Apply patch without reading context first.",
                success=False,
            )

            results = consolidator.recall_procedural(user_id=user, query="multi-file edits", limit=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["strategy_key"], "search_then_patch")
            self.assertGreater(results[0]["success_ratio"], results[1]["success_ratio"])


if __name__ == "__main__":
    unittest.main()
