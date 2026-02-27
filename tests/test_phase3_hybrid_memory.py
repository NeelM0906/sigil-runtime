from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.llm.providers import StaticEchoProvider
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

    def test_conversation_turns_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            tenant_id = "tenant-conv"
            user_id = "user-conv"
            session_id = "session-conv"
            for idx in range(1, 8):
                turn_number = store.record_turn(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    turn_id=f"turn-{idx}",
                    user_id=user_id,
                    user_message=f"user says {idx}",
                    assistant_message=f"assistant says {idx}",
                )
                self.assertEqual(turn_number, idx)

            recent = store.get_recent_turns(tenant_id=tenant_id, session_id=session_id, limit=3)
            self.assertEqual(len(recent), 6)
            self.assertEqual(recent[0]["content"], "user says 5")
            self.assertEqual(recent[-1]["content"], "assistant says 7")

            unsummarized = store.get_turns_for_summary(
                tenant_id=tenant_id,
                session_id=session_id,
                covers_through_turn=0,
                recent_window=3,
            )
            self.assertTrue(unsummarized)
            self.assertEqual(unsummarized[-1]["turn_number"], 4)

            summary = store.generate_session_summary(
                turns=unsummarized,
                provider=StaticEchoProvider(),
                model_id="echo-model",
            )
            self.assertTrue(summary)
            saved = store.update_session_summary(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=user_id,
                summary_text=summary,
                covers_through_turn=4,
            )
            self.assertEqual(saved["covers_through_turn"], 4)
            loaded = store.get_session_summary(tenant_id=tenant_id, session_id=session_id)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded["covers_through_turn"], 4)

    def test_first_summary_boundary_with_three_turn_window(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            tenant_id = "tenant-boundary"
            user_id = "user-boundary"
            session_id = "session-boundary"
            for idx in range(1, 6):
                store.record_turn(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    turn_id=f"turn-{idx}",
                    user_id=user_id,
                    user_message=f"user says {idx}",
                    assistant_message=f"assistant says {idx}",
                )

            turns = store.get_turns_for_summary(
                tenant_id=tenant_id,
                session_id=session_id,
                covers_through_turn=0,
                recent_window=3,
            )
            self.assertEqual([item["turn_number"] for item in turns], [1, 2])

    def test_missing_markdown_file_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            self.assertEqual(store._read_note_body("does/not/exist.md"), "")

    def test_generate_session_summary_logs_on_provider_error(self) -> None:
        class _FailProvider:
            def generate(self, model, messages):  # noqa: ANN001
                _ = (model, messages)
                raise RuntimeError("provider_unavailable")

        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            store = HybridMemoryStore(db=db, memory_root=Path(td) / "memory", auto_apply_confidence=0.4)
            turns = [
                {"turn_number": 1, "user_message": "hello", "assistant_message": "hi"},
                {"turn_number": 2, "user_message": "status?", "assistant_message": "working"},
            ]
            with self.assertLogs("bomba_sr.memory.hybrid", level="WARNING") as captured:
                summary = store.generate_session_summary(
                    turns=turns,
                    provider=_FailProvider(),  # type: ignore[arg-type]
                    model_id="anthropic/claude-opus-4.6",
                )
            self.assertTrue(summary)
            self.assertTrue(any("session summary LLM call failed" in line for line in captured.output))


if __name__ == "__main__":
    unittest.main()
