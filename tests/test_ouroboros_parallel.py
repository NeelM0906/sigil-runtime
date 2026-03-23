from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
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
        if candidate != root.resolve() and root.resolve() not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class _AllReadProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
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
                                    {"id": "r1", "type": "function", "function": {"name": "read_one", "arguments": "{}"}},
                                    {"id": "r2", "type": "function", "function": {"name": "read_two", "arguments": "{}"}},
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
                stop_reason="tool_calls",
            )
        return LLMResponse(
            text="done",
            model=model,
            usage={"prompt_tokens": 8, "completion_tokens": 1},
            raw={"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class _MixedProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
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
                                    {"id": "m1", "type": "function", "function": {"name": "read_one", "arguments": "{}"}},
                                    {"id": "m2", "type": "function", "function": {"name": "write_one", "arguments": "{}"}},
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
                stop_reason="tool_calls",
            )
        return LLMResponse(
            text="done",
            model=model,
            usage={"prompt_tokens": 8, "completion_tokens": 1},
            raw={"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class OuroborosParallelTests(unittest.TestCase):
    def _setup(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name) / "ws"
        root.mkdir(parents=True, exist_ok=True)
        db = RuntimeDB(Path(td.name) / "runtime.db")
        governance = ToolGovernanceService(db)
        governance.upsert_default_policy("tenant-par")
        pipeline = PolicyPipeline(governance)
        executor = ToolExecutor(governance, pipeline)
        executor.register(
            ToolDefinition(
                name="read_one",
                description="read tool",
                parameters={"type": "object", "properties": {}, "additionalProperties": True},
                risk_level="low",
                action_type="read",
                execute=lambda _args, _ctx: (time.sleep(0.2) or {"name": "read_one"}),
            )
        )
        executor.register(
            ToolDefinition(
                name="read_two",
                description="read tool",
                parameters={"type": "object", "properties": {}, "additionalProperties": True},
                risk_level="low",
                action_type="read",
                execute=lambda _args, _ctx: (time.sleep(0.2) or {"name": "read_two"}),
            )
        )
        executor.register(
            ToolDefinition(
                name="write_one",
                description="write tool",
                parameters={"type": "object", "properties": {}, "additionalProperties": True},
                risk_level="medium",
                action_type="write",
                execute=lambda _args, _ctx: (time.sleep(0.2) or {"name": "write_one"}),
            )
        )
        policy = pipeline.resolve(
            ToolPolicyContext(tenant_id="tenant-par"),
            available_tools=executor.known_tool_names(),
        )
        context = ToolContext(
            tenant_id="tenant-par",
            session_id="s1",
            turn_id="t1",
            user_id="u1",
            workspace_root=root,
            db=db,
            guard_path=_guard(root),
        )
        return executor, policy, context

    def test_all_read_calls_execute_in_parallel_and_keep_order(self) -> None:
        executor, policy, context = self._setup()
        loop = AgenticLoop(
            provider=_AllReadProvider(),
            tool_executor=executor,
            config=LoopConfig(max_iterations=5, parallel_read_tools=True, max_parallel_workers=4),
        )
        started = time.monotonic()
        result = loop.run(
            initial_messages=[ChatMessage(role="system", content="sys"), ChatMessage(role="user", content="go")],
            tool_schemas=executor.available_tool_schemas(policy),
            context=context,
            resolved_policy=policy,
            model_id="test-model",
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.35)
        self.assertEqual([tc.tool_name for tc in result.tool_calls], ["read_one", "read_two"])

    def test_mixed_calls_execute_sequentially(self) -> None:
        executor, policy, context = self._setup()
        loop = AgenticLoop(
            provider=_MixedProvider(),
            tool_executor=executor,
            config=LoopConfig(max_iterations=5, parallel_read_tools=True, max_parallel_workers=4),
        )
        started = time.monotonic()
        result = loop.run(
            initial_messages=[ChatMessage(role="system", content="sys"), ChatMessage(role="user", content="go")],
            tool_schemas=executor.available_tool_schemas(policy),
            context=context,
            resolved_policy=policy,
            model_id="test-model",
        )
        elapsed = time.monotonic() - started
        self.assertGreater(elapsed, 0.35)
        self.assertEqual([tc.tool_name for tc in result.tool_calls], ["read_one", "write_one"])


if __name__ == "__main__":
    unittest.main()
