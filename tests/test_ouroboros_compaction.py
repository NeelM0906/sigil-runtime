from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_compaction import builtin_compaction_tools


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate != root.resolve() and root.resolve() not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class _SummaryProvider:
    provider_name = "openai"

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
        return LLMResponse(
            text="summary of prior conversation and outcomes",
            model=model,
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            raw={"choices": [{"message": {"content": "summary"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class OuroborosCompactionTests(unittest.TestCase):
    def test_compaction_reduces_message_count(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            messages = [
                ChatMessage(role="system", content="system prompt"),
                ChatMessage(role="user", content="u1"),
                ChatMessage(role="assistant", content="a1"),
                ChatMessage(role="tool", content="t1"),
                ChatMessage(role="assistant", content="a2"),
                ChatMessage(role="tool", content="t2"),
                ChatMessage(role="assistant", content="a3"),
            ]
            state = SimpleNamespace(messages=messages, current_model_id="anthropic/claude-opus-4.6")
            context = ToolContext(
                tenant_id="tenant-comp",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
                loop_state_ref=state,
            )
            tool = builtin_compaction_tools(_SummaryProvider(), default_model_id="anthropic/claude-opus-4.6")[0]
            result = tool.execute({"reason": "conversation getting long"}, context)
            self.assertTrue(result["compacted"])
            self.assertGreater(result["original_messages"], result["compacted_messages"])
            self.assertLessEqual(len(result["summary"]), 8000)
            self.assertEqual(state.messages[0].role, "system")

    def test_short_conversation_not_compacted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            state = SimpleNamespace(
                messages=[
                    ChatMessage(role="system", content="system"),
                    ChatMessage(role="user", content="u1"),
                    ChatMessage(role="assistant", content="a1"),
                ],
                current_model_id="anthropic/claude-opus-4.6",
            )
            context = ToolContext(
                tenant_id="tenant-comp",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
                loop_state_ref=state,
            )
            tool = builtin_compaction_tools(_SummaryProvider(), default_model_id="anthropic/claude-opus-4.6")[0]
            result = tool.execute({"reason": "not needed"}, context)
            self.assertFalse(result["compacted"])
            self.assertEqual(result["reason"], "conversation_too_short")


if __name__ == "__main__":
    unittest.main()
