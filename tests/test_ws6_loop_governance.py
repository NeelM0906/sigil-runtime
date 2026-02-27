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


class _DeniedThenFinalProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                text="",
                model=model,
                usage={"prompt_tokens": 10, "completion_tokens": 2},
                raw={
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "c-denied",
                                        "type": "function",
                                        "function": {"name": "write", "arguments": json.dumps({"x": 1})},
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
                stop_reason="tool_calls",
            )
        return LLMResponse(
            text="could not run that tool",
            model=model,
            usage={"prompt_tokens": 8, "completion_tokens": 3},
            raw={
                "choices": [
                    {
                        "message": {"content": "could not run that tool"},
                        "finish_reason": "stop",
                    }
                ]
            },
            stop_reason="stop",
        )


class LoopGovernanceTests(unittest.TestCase):
    def test_denied_tool_call_is_returned_in_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-loop-gov")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            executor.register(
                ToolDefinition(
                    name="write",
                    description="write op",
                    parameters={"type": "object", "properties": {"x": {"type": "integer"}}, "additionalProperties": False},
                    risk_level="medium",
                    action_type="write",
                    execute=lambda _args, _ctx: {"ok": True},
                )
            )

            # MINIMAL profile does not allow "write".
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.MINIMAL, tenant_id="tenant-loop-gov"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-loop-gov",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            loop = AgenticLoop(
                provider=_DeniedThenFinalProvider(),
                tool_executor=executor,
                config=LoopConfig(max_iterations=5),
            )
            result = loop.run(
                initial_messages=[ChatMessage(role="system", content="policy test")],
                tool_schemas=executor.available_tool_schemas(policy),
                context=context,
                resolved_policy=policy,
                model_id="test-model",
            )
            self.assertEqual(result.final_text, "could not run that tool")
            self.assertEqual(len(result.tool_calls), 1)
            self.assertEqual(result.tool_calls[0].status, "denied")


if __name__ == "__main__":
    unittest.main()
