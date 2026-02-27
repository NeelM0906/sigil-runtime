from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_model_switch import builtin_model_switch_tools


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


class _SwitchProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.models_used: list[str] = []
        self.calls = 0

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
        self.models_used.append(model)
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                text="",
                model=model,
                usage={"prompt_tokens": 10, "completion_tokens": 1},
                raw={
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "switch-1",
                                        "type": "function",
                                        "function": {
                                            "name": "switch_model",
                                            "arguments": json.dumps(
                                                {"model_id": "anthropic/claude-haiku", "reason": "cheap pass"}
                                            ),
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
            text="done",
            model=model,
            usage={"prompt_tokens": 8, "completion_tokens": 1},
            raw={"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class OuroborosModelSwitchTests(unittest.TestCase):
    def test_switch_tool_updates_loop_state(self) -> None:
        state = SimpleNamespace(current_model_id="old-model")
        tool = builtin_model_switch_tools()[0]
        context = ToolContext(
            tenant_id="t",
            session_id="s",
            turn_id="x",
            user_id="u",
            workspace_root=Path(".").resolve(),
            db=RuntimeDB(":memory:"),
            guard_path=lambda p: Path(p).resolve(),
            loop_state_ref=state,
        )
        out = tool.execute({"model_id": "new-model", "reason": "upgrade"}, context)
        self.assertTrue(out["switched"])
        self.assertEqual(state.current_model_id, "new-model")

    def test_switch_takes_effect_next_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-switch")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            executor.register_many(builtin_model_switch_tools())
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-switch"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-switch",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            provider = _SwitchProvider()
            loop = AgenticLoop(provider=provider, tool_executor=executor, config=LoopConfig(max_iterations=5))
            loop.run(
                initial_messages=[ChatMessage(role="system", content="sys"), ChatMessage(role="user", content="go")],
                tool_schemas=executor.available_tool_schemas(policy),
                context=context,
                resolved_policy=policy,
                model_id="anthropic/claude-opus-4.6",
            )
            self.assertEqual(provider.models_used[0], "anthropic/claude-opus-4.6")
            self.assertEqual(provider.models_used[1], "anthropic/claude-haiku")


if __name__ == "__main__":
    unittest.main()
