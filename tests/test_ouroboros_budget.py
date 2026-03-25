from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.runtime.config import RuntimeConfig
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig, estimate_cost
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor


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


class _HighUsageProvider:
    provider_name = "openai"

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
        return LLMResponse(
            text="budget stop",
            model=model,
            usage={"prompt_tokens": 500_000, "completion_tokens": 500_000},
            raw={"choices": [{"message": {"content": "budget stop"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class OuroborosBudgetTests(unittest.TestCase):
    def test_estimate_cost_known_and_fallback(self) -> None:
        known = estimate_cost("anthropic/claude-opus-4.6", 1_000_000, 1_000_000)
        self.assertAlmostEqual(known, 30.0, places=3)
        fallback = estimate_cost("unknown-model", 1_000_000, 1_000_000)
        self.assertAlmostEqual(fallback, 18.0, places=3)

    def test_budget_hard_stop_sets_budget_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-budget")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-budget"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-budget",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            loop = AgenticLoop(
                provider=_HighUsageProvider(),
                tool_executor=executor,
                config=LoopConfig(
                    max_iterations=5,
                    budget_limit_usd=2.0,
                    budget_hard_stop_pct=0.9,
                ),
            )
            result = loop.run(
                initial_messages=[ChatMessage(role="system", content="system"), ChatMessage(role="user", content="go")],
                tool_schemas=[],
                context=context,
                resolved_policy=policy,
                model_id="anthropic/claude-opus-4.6",
            )
            self.assertEqual(result.stopped_reason, "budget_exhausted")
            self.assertTrue(result.budget_exhausted)
            self.assertGreater(result.estimated_cost_usd, 1.8)

    def test_runtime_config_budget_validation(self) -> None:
        with self.assertRaises(ValueError):
            RuntimeConfig(budget_limit_usd=0.0)
        with self.assertRaises(ValueError):
            RuntimeConfig(budget_hard_stop_pct=0.0)


if __name__ == "__main__":
    unittest.main()
