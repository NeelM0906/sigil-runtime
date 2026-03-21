from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_real = root.resolve()
        if candidate != root_real and root_real not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class _SingleResponseProvider:
    provider_name = "openai"

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:
        return LLMResponse(
            text="final answer",
            model=model,
            usage={"prompt_tokens": 12, "completion_tokens": 5},
            raw={
                "choices": [
                    {
                        "message": {"content": "final answer"},
                        "finish_reason": "stop",
                    }
                ]
            },
            stop_reason="stop",
        )


class AgenticLoopBasicTests(unittest.TestCase):
    def test_no_tool_calls_returns_after_single_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-loop")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-loop"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-loop",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            loop = AgenticLoop(
                provider=_SingleResponseProvider(),
                tool_executor=executor,
                config=LoopConfig(max_iterations=5),
            )
            result = loop.run(
                initial_messages=[ChatMessage(role="system", content="You are helpful")],
                tool_schemas=[],
                context=context,
                resolved_policy=policy,
                model_id="test-model",
            )
            self.assertEqual(result.iterations, 1)
            self.assertEqual(result.final_text, "final answer")
            self.assertEqual(result.tool_calls, [])
            self.assertEqual(result.total_input_tokens, 12)
            self.assertEqual(result.total_output_tokens, 5)


if __name__ == "__main__":
    unittest.main()
