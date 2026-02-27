from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolDefinition, ToolExecutor


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


class _RepeatingToolProvider:
    provider_name = "openai"

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:
        return LLMResponse(
            text="",
            model=model,
            usage={"prompt_tokens": 5, "completion_tokens": 2},
            raw={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "repeat-call",
                                    "type": "function",
                                    "function": {"name": "loop_tool", "arguments": json.dumps({"x": 1})},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
            stop_reason="tool_calls",
        )


class LoopDetectionTests(unittest.TestCase):
    def test_stops_on_repeated_identical_tool_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-loop-detect")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            executor.register(
                ToolDefinition(
                    name="loop_tool",
                    description="Always returns same output",
                    parameters={"type": "object", "properties": {"x": {"type": "integer"}}, "additionalProperties": False},
                    risk_level="low",
                    action_type="read",
                    execute=lambda _args, _ctx: {"same": True},
                )
            )
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-loop-detect"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-loop-detect",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )

            loop = AgenticLoop(
                provider=_RepeatingToolProvider(),
                tool_executor=executor,
                config=LoopConfig(max_iterations=10, loop_detection_window=2),
            )
            result = loop.run(
                initial_messages=[ChatMessage(role="system", content="loop test")],
                tool_schemas=executor.available_tool_schemas(policy),
                context=context,
                resolved_policy=policy,
                model_id="test-model",
            )
            self.assertEqual(result.stopped_reason, "loop_detected")
            self.assertGreaterEqual(result.iterations, 2)
            self.assertTrue(result.tool_calls)


if __name__ == "__main__":
    unittest.main()
