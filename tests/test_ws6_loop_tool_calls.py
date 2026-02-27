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
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_fs import builtin_fs_tools


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


class _TwoStepProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self._calls = 0

    def generate(self, model: str, messages: list[ChatMessage], tools=None) -> LLMResponse:
        self._calls += 1
        if self._calls == 1:
            return LLMResponse(
                text="",
                model=model,
                usage={"prompt_tokens": 10, "completion_tokens": 3},
                raw={
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "read",
                                            "arguments": json.dumps({"path": "README.md"}),
                                        },
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
            text="Read completed and summarized.",
            model=model,
            usage={"prompt_tokens": 11, "completion_tokens": 4},
            raw={
                "choices": [
                    {
                        "message": {"content": "Read completed and summarized."},
                        "finish_reason": "stop",
                    }
                ]
            },
            stop_reason="stop",
        )


class AgenticLoopToolCallTests(unittest.TestCase):
    def test_tool_call_executes_and_second_iteration_returns_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text("line1\nline2\n", encoding="utf-8")

            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-loop-tools")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            executor.register_many(builtin_fs_tools())
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-loop-tools"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-loop-tools",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            loop = AgenticLoop(
                provider=_TwoStepProvider(),
                tool_executor=executor,
                config=LoopConfig(max_iterations=5),
            )
            result = loop.run(
                initial_messages=[ChatMessage(role="system", content="You are helpful")],
                tool_schemas=executor.available_tool_schemas(policy, format="openai"),
                context=context,
                resolved_policy=policy,
                model_id="test-model",
            )
            self.assertEqual(result.iterations, 2)
            self.assertEqual(result.final_text, "Read completed and summarized.")
            self.assertEqual(len(result.tool_calls), 1)
            self.assertEqual(result.tool_calls[0].tool_name, "read")
            self.assertEqual(result.tool_calls[0].status, "executed")


if __name__ == "__main__":
    unittest.main()
