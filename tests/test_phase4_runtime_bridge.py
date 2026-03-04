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
            first_session_id = due[0]["result"]["session_id"]

            runtime.db.execute(
                "UPDATE scheduled_tasks SET next_run_at = ? WHERE id = ?",
                ((datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(), created["id"]),
            )
            runtime.db.commit()
            due_again = bridge.run_due_schedules_once(
                tenant_id="tenant-autonomy",
                user_id="user-autonomy",
                workspace_root=str(workspace),
            )
            self.assertEqual(len(due_again), 1)
            second_session_id = due_again[0]["result"]["session_id"]
            self.assertNotEqual(first_session_id, second_session_id)
            self.assertTrue(first_session_id.startswith(f"scheduled-{created['id']}-"))
            self.assertTrue(second_session_id.startswith(f"scheduled-{created['id']}-"))
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

    def test_web_tools_registration_respects_config_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home_disabled = Path(td) / "runtime-home-disabled"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge_disabled = RuntimeBridge(
                config=RuntimeConfig(
                    runtime_home=runtime_home_disabled,
                    web_search_enabled=False,
                ),
                provider=StaticEchoProvider(),
            )
            runtime_disabled = bridge_disabled._tenant_runtime("tenant-web-disabled", str(workspace))
            names_disabled = runtime_disabled.tool_executor.known_tool_names()
            self.assertNotIn("web_search", names_disabled)
            self.assertNotIn("web_fetch", names_disabled)

            runtime_home_enabled = Path(td) / "runtime-home-enabled"
            bridge_enabled = RuntimeBridge(
                config=RuntimeConfig(
                    runtime_home=runtime_home_enabled,
                    web_search_enabled=True,
                ),
                provider=StaticEchoProvider(),
            )
            runtime_enabled = bridge_enabled._tenant_runtime("tenant-web-enabled", str(workspace))
            names_enabled = runtime_enabled.tool_executor.known_tool_names()
            self.assertIn("web_search", names_enabled)
            self.assertIn("web_fetch", names_enabled)


class TestStripToolBlocks(unittest.TestCase):
    """Verify _strip_tool_blocks removes tool blocks and keeps text."""

    def test_strip_removes_tool_role_messages(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        messages = [
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": "sure, calling tool"},
            {"role": "tool", "content": "tool result here"},
        ]
        cleaned = _strip_tool_blocks(messages)
        roles = [m["role"] for m in cleaned]
        self.assertNotIn("tool", roles)
        self.assertEqual(len(cleaned), 2)

    def test_strip_keeps_string_content(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        cleaned = _strip_tool_blocks(messages)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["content"], "hello")
        self.assertEqual(cleaned[1]["content"], "world")

    def test_strip_filters_list_content_to_text_only(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "Let me search"},
                {"type": "tool_use", "id": "t1", "name": "web_search", "input": {}},
            ]},
        ]
        cleaned = _strip_tool_blocks(messages)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(cleaned[0]["content"]), 1)
        self.assertEqual(cleaned[0]["content"][0]["type"], "text")

    def test_strip_drops_message_with_only_tool_blocks(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
            ]},
        ]
        cleaned = _strip_tool_blocks(messages)
        self.assertEqual(len(cleaned), 0)

    def test_strip_empty_input(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        self.assertEqual(_strip_tool_blocks([]), [])

    def test_strip_preserves_message_metadata(self) -> None:
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        messages = [
            {"role": "user", "content": "test", "extra_key": "preserved"},
        ]
        cleaned = _strip_tool_blocks(messages)
        self.assertEqual(cleaned[0]["extra_key"], "preserved")


class TestOrchSubtaskReplay(unittest.TestCase):
    """Verify orchestration/subtask sessions get stripped replay, not zero replay."""

    def test_subtask_session_gets_replay(self) -> None:
        """A subtask session should replay previous turns (stripped), not skip them."""
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            provider = CaptureProvider()
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=provider,
            )
            session_id = "subtask:task-abc:forge"
            # Turn 1
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-sub",
                    session_id=session_id,
                    user_id="forge",
                    user_message="first pass at the task",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            # Turn 2 (revision round)
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-sub",
                    session_id=session_id,
                    user_id="forge",
                    user_message="revise: expand section 3",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertGreaterEqual(len(provider.calls), 2)
            second_call = provider.calls[1]
            # The second call should contain replay of the first turn's content
            all_content = " ".join(
                getattr(m, "content", "") for m in second_call
                if isinstance(getattr(m, "content", ""), str)
            )
            self.assertIn("first pass at the task", all_content)

    def test_orchestration_session_gets_replay(self) -> None:
        """An orchestration session should also get stripped replay."""
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            provider = CaptureProvider()
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=provider,
            )
            session_id = "orchestration:task-xyz"
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-orch",
                    session_id=session_id,
                    user_id="orchestrator",
                    user_message="plan the task",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-orch",
                    session_id=session_id,
                    user_id="orchestrator",
                    user_message="now synthesize",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertGreaterEqual(len(provider.calls), 2)
            second_call = provider.calls[1]
            all_content = " ".join(
                getattr(m, "content", "") for m in second_call
                if isinstance(getattr(m, "content", ""), str)
            )
            self.assertIn("plan the task", all_content)


class TestBeingIdInBridge(unittest.TestCase):
    """Verify being_id propagation through handle_turn's memory writes."""

    def test_being_id_resolved_for_mc_chat_session(self):
        """Memory writes in mc-chat-{being_id} sessions set being_id."""
        from bomba_sr.memory.hybrid import resolve_being_id
        bid = resolve_being_id("mc-chat-forge")
        self.assertEqual(bid, "forge")

    def test_being_id_resolved_for_subtask_session(self):
        """Memory writes in subtask sessions set being_id."""
        from bomba_sr.memory.hybrid import resolve_being_id
        bid = resolve_being_id("subtask:task-123:scholar")
        self.assertEqual(bid, "scholar")

    def test_being_id_none_for_orchestration_session(self):
        """Orchestration sessions (prime) don't map to a specific being."""
        from bomba_sr.memory.hybrid import resolve_being_id
        bid = resolve_being_id("orchestration:task-123")
        self.assertIsNone(bid)

    def test_being_id_from_user_id_fallback(self):
        """When session doesn't match, falls back to user_id pattern."""
        from bomba_sr.memory.hybrid import resolve_being_id
        bid = resolve_being_id("some-session", "prime->recovery")
        self.assertEqual(bid, "recovery")

    def test_strip_tool_blocks_with_being_id(self):
        """Ensure _strip_tool_blocks still works after being_id changes."""
        from bomba_sr.runtime.bridge import _strip_tool_blocks
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = _strip_tool_blocks(msgs)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
