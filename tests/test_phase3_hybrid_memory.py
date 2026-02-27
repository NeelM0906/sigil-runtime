from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.memory.hybrid import HybridMemoryStore
from bomba_sr.storage.db import RuntimeDB


class HybridMemoryTests(unittest.TestCase):
    def test_confidence_gate_and_approval(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            user_id = str(uuid.uuid4())

            high = store.learn_semantic(
                tenant_id="tenant-1",
                user_id=user_id,
                memory_key="pref_editor",
                content="User prefers Neovim",
                confidence=0.8,
            )
            self.assertEqual(high.status, "applied")
            self.assertTrue(high.memory_id)

            low = store.learn_semantic(
                tenant_id="tenant-1",
                user_id=user_id,
                memory_key="pref_shell",
                content="User may like fish shell",
                confidence=0.2,
            )
            self.assertEqual(low.status, "pending")

            pending = store.pending_approvals("tenant-1", user_id)
            self.assertEqual(len(pending), 1)

            approved = store.approve_learning(low.update_id, approved=True)
            self.assertEqual(approved.status, "applied")
            self.assertTrue(approved.memory_id)

    def test_markdown_note_recall(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            note = store.append_working_note(
                user_id=user_id,
                session_id=session_id,
                title="Deploy process",
                content="Deploy uses canary then full rollout",
                tags=["deploy"],
            )
            self.assertTrue(Path(note["path"]).exists())

            recalled = store.recall(user_id=user_id, query="canary rollout", limit=6)
            self.assertTrue(recalled["markdown"])
            self.assertIn("canary", recalled["markdown"][0]["snippet"].lower())


if __name__ == "__main__":
    unittest.main()
