from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import LLMResponse, StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class CaptureProvider:
    provider_name = "capture"

    def __init__(self) -> None:
        self.calls: list[list] = []
        self.counter = 0

    def generate(self, model: str, messages: list, tools=None) -> LLMResponse:  # noqa: ANN001
        self.calls.append(list(messages))
        self.counter += 1
        return LLMResponse(
            text=f"assistant-{self.counter}",
            model=model,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            raw={"echo": True},
            stop_reason="stop",
        )


class RuntimeBridgeTests(unittest.TestCase):
    def test_handle_turn_records_learning_without_artifact_for_simple_chat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "main.py").write_text("def payment_handler():\n    return 1\n", encoding="utf-8")

            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )

            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-d",
                    session_id=str(uuid.uuid4()),
                    user_id="user-d",
                    user_message="I prefer Neovim for coding",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )

            self.assertIn("assistant", result)
            self.assertTrue(result["assistant"]["text"])
            self.assertEqual(result["artifacts"], [])
            self.assertTrue(result["codeintel"]["serena_enabled"])
            self.assertTrue(result["codeintel"]["serena_edit_tools_enabled"])
            self.assertIn(result["memory"]["learning"]["status"], {"applied", "pending"})

    def test_handle_turn_creates_markdown_artifact_on_explicit_deliverable_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-deliverable",
                    session_id=str(uuid.uuid4()),
                    user_id="user-deliverable",
                    user_message="create a markdown report for today status",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )

            self.assertTrue(result["artifacts"])
            self.assertEqual(result["artifacts"][0]["type"], "markdown")

    def test_replays_recent_conversation_turns_in_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            provider = CaptureProvider()
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=provider,
            )
            session_id = str(uuid.uuid4())
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-replay",
                    session_id=session_id,
                    user_id="user-replay",
                    user_message="first-message",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-replay",
                    session_id=session_id,
                    user_id="user-replay",
                    user_message="second-message",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertGreaterEqual(len(provider.calls), 2)
            second_messages = provider.calls[1]
            replay_user = [m for m in second_messages if getattr(m, "role", "") == "user" and m.content == "first-message"]
            replay_assistant = [m for m in second_messages if getattr(m, "role", "") == "assistant" and m.content == "assistant-1"]
            self.assertTrue(replay_user)
            self.assertTrue(replay_assistant)

    def test_autonomy_scheduler_management(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(
                    runtime_home=runtime_home,
                    cron_enabled=True,
                    heartbeat_enabled=False,
                ),
                provider=StaticEchoProvider(),
            )
            bridge.start_autonomy(tenant_id="tenant-autonomy", user_id="user-autonomy", workspace_root=str(workspace))
            created = bridge.add_schedule(
                tenant_id="tenant-autonomy",
                user_id="user-autonomy",
                cron_expression="*/1 * * * *",
                task_goal="check TODOs",
                workspace_root=str(workspace),
            )
            schedules = bridge.list_schedules(
                tenant_id="tenant-autonomy",
                user_id="user-autonomy",
                workspace_root=str(workspace),
            )
            self.assertEqual(len(schedules), 1)

            runtime = bridge._tenant_runtime("tenant-autonomy", str(workspace))
            runtime.db.execute(
                "UPDATE scheduled_tasks SET next_run_at = ? WHERE id = ?",
                ((datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(), created["id"]),
            )
            runtime.db.commit()

            due = bridge.run_due_schedules_once(
                tenant_id="tenant-autonomy",
                user_id="user-autonomy",
                workspace_root=str(workspace),
            )
            self.assertEqual(len(due), 1)
            removed = bridge.remove_schedule(
                tenant_id="tenant-autonomy",
                user_id="user-autonomy",
                task_id=created["id"],
                workspace_root=str(workspace),
            )
            self.assertTrue(removed["removed"])

    def test_summary_generated_on_fifth_turn_with_three_turn_window(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )
            tenant_id = "tenant-summary-5"
            session_id = str(uuid.uuid4())
            user_id = "user-summary-5"
            for idx in range(1, 6):
                bridge.handle_turn(
                    TurnRequest(
                        tenant_id=tenant_id,
                        session_id=session_id,
                        user_id=user_id,
                        user_message=f"message {idx}",
                        profile=TurnProfile.CHAT,
                        workspace_root=str(workspace),
                    )
                )

            runtime = bridge._tenant_runtime(tenant_id, str(workspace))
            summary = runtime.memory.get_session_summary(tenant_id=tenant_id, session_id=session_id)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(int(summary["covers_through_turn"]), 2)

    def test_replay_messages_are_capped_by_token_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            provider = CaptureProvider()
            bridge = RuntimeBridge(
                config=RuntimeConfig(
                    runtime_home=runtime_home,
                    replay_history_budget_fraction=0.001,
                ),
                provider=provider,
            )
            session_id = str(uuid.uuid4())
            large_message = "A" * 12000
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-replay-cap",
                    session_id=session_id,
                    user_id="user-replay-cap",
                    user_message=large_message,
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-replay-cap",
                    session_id=session_id,
                    user_id="user-replay-cap",
                    user_message="follow-up",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertGreaterEqual(len(provider.calls), 2)
            second_messages = provider.calls[1]
            replayed_large = [
                m for m in second_messages
                if getattr(m, "role", "") == "user" and getattr(m, "content", "") == large_message
            ]
            self.assertEqual(replayed_large, [])

    def test_command_turn_is_persisted_in_conversation_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )
            tenant_id = "tenant-command-history"
            session_id = str(uuid.uuid4())
            user_id = "user-command-history"
            bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    user_id=user_id,
                    user_message="/help",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            runtime = bridge._tenant_runtime(tenant_id, str(workspace))
            rows = runtime.memory.get_recent_turn_records(tenant_id=tenant_id, session_id=session_id, limit=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["user_message"], "/help")
            self.assertIn("commands", rows[0]["assistant_message"])

    def test_skill_nl_turn_is_persisted_in_conversation_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )
            tenant_id = "tenant-nl-history"
            session_id = str(uuid.uuid4())
            user_id = "user-nl-history"
            message = "list skills from clawhub"
            bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message,
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            runtime = bridge._tenant_runtime(tenant_id, str(workspace))
            rows = runtime.memory.get_recent_turn_records(tenant_id=tenant_id, session_id=session_id, limit=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["user_message"], message)
            self.assertIn("catalog_list", rows[0]["assistant_message"])


if __name__ == "__main__":
    unittest.main()
