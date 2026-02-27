from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone

from bomba_sr.adaptation.self_evaluation import SelfEvaluator
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.storage.db import RuntimeDB


class _JSONProvider:
    provider_name = "json_test"

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:  # noqa: ANN001
        return LLMResponse(
            text='{"tool_efficiency":0.8,"memory_quality":0.7,"goal_completion":0.9,"recommendations":["keep"],"policy_updates":{"max_loop_iterations":20}}',
            model=model,
            usage=None,
            raw={"ok": True},
            stop_reason="stop",
        )


class _TextProvider:
    provider_name = "text_test"

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:  # noqa: ANN001
        return LLMResponse(
            text="not-json",
            model=model,
            usage=None,
            raw={"ok": True},
            stop_reason="stop",
        )


class SelfEvaluationTests(unittest.TestCase):
    def test_evaluate_reads_loop_executions_and_parses_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            db.script(
                """
                CREATE TABLE IF NOT EXISTS loop_executions (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  turn_id TEXT NOT NULL,
                  iterations INTEGER NOT NULL,
                  tool_calls_json TEXT NOT NULL,
                  stopped_reason TEXT,
                  total_input_tokens INTEGER,
                  total_output_tokens INTEGER,
                  duration_ms INTEGER,
                  created_at TEXT NOT NULL
                );
                """
            )
            db.execute(
                """
                INSERT INTO loop_executions (
                  id, tenant_id, session_id, turn_id, iterations, tool_calls_json, stopped_reason,
                  total_input_tokens, total_output_tokens, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "l1",
                    "t1",
                    "s1",
                    "turn-1",
                    2,
                    "[]",
                    None,
                    100,
                    40,
                    1200,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            db.commit()

            evaluator = SelfEvaluator(provider=_JSONProvider(), db=db)
            result = evaluator.evaluate(tenant_id="t1", session_id="s1", model_id="anthropic/claude-opus-4.6")
            self.assertEqual(result["evaluated_loops"], 1)
            self.assertAlmostEqual(result["tool_efficiency"], 0.8, places=6)
            self.assertEqual(result["policy_updates"]["max_loop_iterations"], 20)

    def test_evaluate_fallback_when_provider_returns_plain_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            db.script(
                """
                CREATE TABLE IF NOT EXISTS loop_executions (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  turn_id TEXT NOT NULL,
                  iterations INTEGER NOT NULL,
                  tool_calls_json TEXT NOT NULL,
                  stopped_reason TEXT,
                  total_input_tokens INTEGER,
                  total_output_tokens INTEGER,
                  duration_ms INTEGER,
                  created_at TEXT NOT NULL
                );
                """
            )
            db.commit()

            evaluator = SelfEvaluator(provider=_TextProvider(), db=db)
            result = evaluator.evaluate(tenant_id="t1", session_id="s1", model_id="anthropic/claude-opus-4.6")
            self.assertEqual(result["evaluated_loops"], 0)
            self.assertEqual(result["policy_updates"], {})
            self.assertEqual(result["recommendations"], [])
            self.assertAlmostEqual(result["goal_completion"], 0.5, places=6)


if __name__ == "__main__":
    unittest.main()
