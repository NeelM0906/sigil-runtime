from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.llm.providers import ChatMessage, LLMResponse
from bomba_sr.runtime.health import build_health_snapshot
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
        if candidate != root.resolve() and root.resolve() not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class _HealthProbeProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self._calls = 0
        self.messages_seen: list[list[ChatMessage]] = []

    def generate(self, model: str, messages, tools=None) -> LLMResponse:
        self.messages_seen.append(list(messages))
        self._calls += 1
        if self._calls == 1:
            return LLMResponse(
                text="",
                model=model,
                usage={"prompt_tokens": 12, "completion_tokens": 3},
                raw={
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-health",
                                        "type": "function",
                                        "function": {"name": "missing_read_tool", "arguments": "{}"},
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
            usage={"prompt_tokens": 8, "completion_tokens": 4},
            raw={"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
            stop_reason="stop",
        )


class OuroborosHealthTests(unittest.TestCase):
    def test_health_snapshot_text_contains_budget_and_counts(self) -> None:
        fake_state = SimpleNamespace(
            iteration=2,
            tool_calls_history=[
                SimpleNamespace(status="executed"),
                SimpleNamespace(status="error"),
                SimpleNamespace(status="denied"),
                SimpleNamespace(status="approval_required"),
            ],
            estimated_cost_usd=1.0,
            current_model_id="anthropic/claude-opus-4.6",
        )
        fake_cfg = SimpleNamespace(max_iterations=10, budget_limit_usd=2.0)
        snapshot = build_health_snapshot(fake_state, fake_cfg, "anthropic/claude-opus-4.6")
        text = snapshot.as_system_text()
        self.assertIn("<health_status>", text)
        self.assertIn("iteration: 2/10", text)
        self.assertIn("$1.0000 / $2.00", text)
        self.assertIn("1 failed", text)

    def test_loop_injects_health_as_replaceable_user_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-health")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance, pipeline)
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-health"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-health",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            provider = _HealthProbeProvider()
            loop = AgenticLoop(provider=provider, tool_executor=executor, config=LoopConfig(max_iterations=2))
            loop.run(
                initial_messages=[ChatMessage(role="system", content="sys"), ChatMessage(role="user", content="go")],
                tool_schemas=[],
                context=context,
                resolved_policy=policy,
                model_id="anthropic/claude-opus-4.6",
            )
            self.assertGreaterEqual(len(provider.messages_seen), 2)
            first_call_system = provider.messages_seen[0][0].content
            self.assertIsInstance(first_call_system, str)
            self.assertNotIn("<health_status>", first_call_system)
            second_call_user_messages = [
                m.content for m in provider.messages_seen[1] if m.role == "user" and isinstance(m.content, str)
            ]
            self.assertTrue(any("<health_status>" in text for text in second_call_user_messages))


if __name__ == "__main__":
    unittest.main()
