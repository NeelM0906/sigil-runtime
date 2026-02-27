from __future__ import annotations

import unittest

from bomba_sr.context.policy import ContextPolicyEngine, TurnProfile


class ContextPolicyTests(unittest.TestCase):
    def test_preserves_constraints_and_sources(self) -> None:
        engine = ContextPolicyEngine()
        result = engine.assemble(
            profile=TurnProfile.TASK_EXECUTION,
            model_context_length=32_000,
            system_contract="Act within contract bounds.",
            user_message="Fix the build and don't touch payment code.",
            inputs={
                "explicit_user_constraints": ["Do not modify payment service"],
                "task_state": {"text": "Current task: fix compile failure"},
                "working_memory": [{"text": "Compiler error in parser.ts line 42"}],
                "world_state": {"text": "repo_state: dirty"},
                "semantic_candidates": [
                    {
                        "text": "Payment service is managed by another team",
                        "source": "mem://semantic/abc",
                        "contradictory": True,
                        "recency_label": "2026-02-20",
                    }
                ],
                "recent_history": [{"text": "User asked to keep payment unchanged"}],
                "procedural_candidates": [{"text": "Run tests after patch"}],
                "pending_predictions": [{"text": "User may ask for diff summary"}],
                "tool_results": [
                    {"source": "tool://read/src/parser.ts#L42", "text": "Unexpected token"}
                ],
            },
        )
        self.assertIn("Do not modify payment service", result.context_text)
        self.assertIn("tool://read/src/parser.ts#L42", result.context_text)
        self.assertIn("recency:", result.context_text)

    def test_pre_compaction_flush_threshold(self) -> None:
        should = ContextPolicyEngine.should_trigger_pre_compaction_flush(
            token_estimate=177000,
            context_window=200000,
            reserve_tokens_floor=20000,
            soft_threshold_tokens=4000,
        )
        self.assertTrue(should)


if __name__ == "__main__":
    unittest.main()
