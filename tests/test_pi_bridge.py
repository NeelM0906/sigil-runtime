"""Tests for the Pi coding agent RPC bridge."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.dashboard.pi_bridge import (
    CRASH_COOLDOWN_S,
    CRASH_MAX,
    CRASH_WINDOW_S,
    PiBridge,
    PiEvent,
    PiSession,
)

WORKSPACE = str(Path(__file__).resolve().parent.parent)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeProc:
    """Simulates a subprocess.Popen with stdin/stdout/stderr pipes."""

    def __init__(self, events: list[dict] | None = None):
        self._events = events or []
        self._stdin_lines: list[str] = []
        self._alive = True
        self._returncode = None

        # stdout: feed events as JSONL lines
        self.stdout = self._make_stdout()
        self.stderr = iter([])  # empty stderr
        self.stdin = self._make_stdin()

    def _make_stdout(self):
        for evt in self._events:
            yield json.dumps(evt) + "\n"

    def _make_stdin(self):
        class FakeStdin:
            def __init__(self, parent):
                self._parent = parent
            def write(self, data):
                self._parent._stdin_lines.append(data)
            def flush(self):
                pass
            def close(self):
                pass
        return FakeStdin(self)

    def poll(self):
        return self._returncode

    def terminate(self):
        self._returncode = -15
        self._alive = False

    def kill(self):
        self._returncode = -9
        self._alive = False

    def wait(self, timeout=None):
        return self._returncode


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestPiSession:
    def test_create(self):
        s = PiSession(id="test-1", title="Test", workspace_root="/tmp")
        assert s.id == "test-1"
        assert s.title == "Test"
        assert s.message_count == 0
        assert s.is_streaming is False


class TestPiBridgeInit:
    def test_defaults(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        assert bridge.workspace_root == "/tmp/test"
        assert bridge.model == "openrouter/anthropic/claude-sonnet-4"
        assert bridge.tools == "read,bash,edit,write,grep,find,ls"
        assert bridge.running is False

    def test_health_not_running(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        h = bridge.health()
        assert h["running"] is False
        assert h["session_count"] == 0


class TestPiBridgeSessions:
    def test_create_session(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        # Mock the subprocess so ensure_running doesn't fail
        bridge._proc = FakeProc()
        bridge._reader_thread = threading.Thread(target=lambda: None)

        session = bridge.create_session("My coding task")
        assert session.title == "My coding task"
        assert session.id.startswith("code-")
        assert bridge._active_session_id == session.id

    def test_list_sessions(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        bridge._proc = FakeProc()
        bridge._reader_thread = threading.Thread(target=lambda: None)

        bridge.create_session("Session 1")
        bridge.create_session("Session 2")
        sessions = bridge.list_sessions()
        assert len(sessions) == 2
        # Most recent first
        assert sessions[0]["title"] == "Session 2"

    def test_delete_session(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        bridge._proc = FakeProc()
        bridge._reader_thread = threading.Thread(target=lambda: None)

        session = bridge.create_session("To delete")
        assert bridge.delete_session(session.id) is True
        assert bridge.delete_session("nonexistent") is False

    def test_send_prompt_unknown_session(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        with pytest.raises(ValueError, match="Unknown session"):
            bridge.send_prompt("nonexistent", "hello")


class TestPiBridgeEventDispatch:
    def test_text_delta_dispatch(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "message_update",
            "assistantMessageEvent": {
                "type": "text_delta",
                "delta": "Hello",
            },
        })

        assert len(collected) == 1
        assert collected[0].event_type == "code_text_delta"
        assert collected[0].data["delta"] == "Hello"
        assert collected[0].session_id == "sess-1"

    def test_text_end_dispatch(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "message_update",
            "assistantMessageEvent": {
                "type": "text_end",
                "content": "Full response here",
            },
        })

        assert len(collected) == 1
        assert collected[0].event_type == "code_text_end"
        assert collected[0].data["content"] == "Full response here"

    def test_tool_call_events(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "message_update",
            "assistantMessageEvent": {
                "type": "toolcall_start",
                "toolName": "read",
                "toolCallId": "tc-1",
            },
        })
        bridge._dispatch_event({
            "type": "message_update",
            "assistantMessageEvent": {
                "type": "toolcall_end",
                "toolName": "read",
                "arguments": '{"path": "src/main.py"}',
            },
        })

        assert len(collected) == 2
        assert collected[0].event_type == "code_tool_call_start"
        assert collected[0].data["tool_name"] == "read"
        assert collected[1].event_type == "code_tool_call_end"

    def test_agent_lifecycle_events(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({"type": "agent_start"})
        assert bridge._sessions["sess-1"].is_streaming is True

        bridge._dispatch_event({"type": "agent_end"})
        assert bridge._sessions["sess-1"].is_streaming is False

        assert collected[0].event_type == "code_agent_start"
        assert collected[1].event_type == "code_agent_end"

    def test_tool_execution_events(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({"type": "tool_execution_start", "toolName": "bash"})
        bridge._dispatch_event({"type": "tool_execution_end", "toolName": "bash", "result": "ok"})

        assert collected[0].event_type == "code_tool_exec_start"
        assert collected[0].data["tool_name"] == "bash"
        assert collected[1].event_type == "code_tool_exec_end"
        assert "result_preview" in collected[1].data

    def test_message_end_extracts_usage(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Done"}],
                "usage": {"input": 100, "output": 50, "cacheRead": 0, "totalTokens": 150, "cost": {"total": 0.001}},
            },
        })

        assert collected[0].event_type == "code_message_end"
        assert collected[0].data["text"] == "Done"
        assert collected[0].data["usage"]["input_tokens"] == 100
        assert collected[0].data["usage"]["cost"] == 0.001

    def test_response_correlation(self):
        bridge = PiBridge(workspace_root="/tmp/test")

        # Simulate pending command
        evt = threading.Event()
        result = {}
        with bridge._pending_lock:
            bridge._pending["cmd-abc"] = (evt, result)

        bridge._dispatch_event({
            "type": "response",
            "id": "cmd-abc",
            "command": "prompt",
            "success": True,
        })

        assert evt.is_set()
        assert result["success"] is True


class TestPiBridgeApprovalFlow:
    def test_extension_ui_request_dispatches_approval(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "extension_ui_request",
            "id": "req-123",
            "method": "select",
            "title": "Allow write?",
            "message": "Agent wants to write /tmp/foo.txt",
            "options": ["Allow", "Deny", "Allow for session"],
        })

        assert len(collected) == 1
        assert collected[0].event_type == "code_approval_required"
        assert collected[0].data["request_id"] == "req-123"
        assert collected[0].data["method"] == "select"
        assert collected[0].data["title"] == "Allow write?"
        assert "Allow" in collected[0].data["options"]

    def test_extension_ui_confirm_dispatches_approval(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "extension_ui_request",
            "id": "req-456",
            "method": "confirm",
            "title": "Clear session?",
            "message": "All messages will be lost.",
        })

        assert len(collected) == 1
        assert collected[0].event_type == "code_approval_required"
        assert collected[0].data["method"] == "confirm"

    def test_fire_and_forget_dispatches_notification(self):
        collected: list[PiEvent] = []
        bridge = PiBridge(workspace_root="/tmp/test", on_event=collected.append)
        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "extension_ui_request",
            "id": "req-789",
            "method": "notify",
            "title": "Info",
            "message": "Task completed",
            "level": "info",
        })

        assert len(collected) == 1
        assert collected[0].event_type == "code_notification"
        assert collected[0].data["message"] == "Task completed"

    def test_respond_ui_not_running(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        with pytest.raises(RuntimeError, match="not running"):
            bridge.respond_ui("req-1", {"confirmed": True})


class TestPiBridgeSubscription:
    def test_subscribe_and_receive(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        sub_id, q = bridge.subscribe()

        bridge._active_session_id = "sess-1"
        bridge._sessions["sess-1"] = PiSession(id="sess-1", title="t", workspace_root="/tmp")

        bridge._dispatch_event({
            "type": "message_update",
            "assistantMessageEvent": {"type": "text_delta", "delta": "hi"},
        })

        event = q.get(timeout=1)
        assert event.event_type == "code_text_delta"
        assert event.data["delta"] == "hi"

        bridge.unsubscribe(sub_id)
        assert sub_id not in bridge._subscribers


class TestPiBridgeFileBrowsing:
    def test_file_tree_returns_entries(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        tree = bridge.file_tree(max_depth=1)
        assert isinstance(tree, list)
        assert len(tree) > 0
        # Should contain src/ and pyproject.toml at minimum
        names = [e["name"] for e in tree]
        assert "src" in names
        assert "pyproject.toml" in names

    def test_file_tree_skips_hidden_and_venv(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        tree = bridge.file_tree(max_depth=1)
        names = [e["name"] for e in tree]
        assert ".git" not in names
        assert ".venv" not in names
        assert "node_modules" not in names

    def test_file_tree_has_children(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        tree = bridge.file_tree(max_depth=2)
        src = next((e for e in tree if e["name"] == "src"), None)
        assert src is not None
        assert src["type"] == "dir"
        assert len(src["children"]) > 0

    def test_read_file_success(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        result = bridge.read_file("pyproject.toml")
        assert "content" in result
        assert "bomba" in result["content"].lower()
        assert result["size"] > 0
        assert result["truncated"] is False

    def test_read_file_not_found(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        with pytest.raises(FileNotFoundError):
            bridge.read_file("nonexistent_file_xyz.txt")

    def test_read_file_path_traversal(self):
        bridge = PiBridge(workspace_root=WORKSPACE)
        with pytest.raises(ValueError, match="traversal"):
            bridge.read_file("../../etc/passwd")


class TestPiBridgeCrashRecovery:
    def test_crash_cooldown(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        now = time.time()
        bridge._crash_times = [now - 10, now - 5, now - 1]

        with pytest.raises(RuntimeError, match="cooldown"):
            bridge.ensure_running()

        assert bridge._cooldown_until > now

    def test_old_crashes_ignored(self):
        bridge = PiBridge(workspace_root="/tmp/test")
        old = time.time() - CRASH_WINDOW_S - 10
        bridge._crash_times = [old, old, old]

        # Should not raise — old crashes are pruned
        # Will raise RuntimeError for process not running, not cooldown
        with patch.object(bridge, "start"):
            bridge.ensure_running()  # no crash-related error


# ---------------------------------------------------------------------------
# Integration test (requires Pi installed + OPENROUTER_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
@pytest.mark.skipif(
    subprocess.run(["which", "pi"], capture_output=True).returncode != 0,
    reason="pi CLI not installed",
)
class TestPiBridgeIntegration:
    """Live integration test — spawns real Pi process."""

    def test_full_round_trip(self):
        env_file = Path(WORKSPACE) / ".env"
        bridge = PiBridge(
            workspace_root=WORKSPACE,
            model="openrouter/anthropic/claude-haiku-4.5",
            thinking="off",
            env_file=str(env_file) if env_file.exists() else None,
        )

        collected: list[PiEvent] = []
        bridge._on_event = collected.append

        try:
            bridge.start()
            assert bridge.running

            session = bridge.create_session("Integration test")

            # Send prompt (don't wait for response since it's async)
            bridge.send_prompt(session.id, "Say exactly: integration test passed")

            # Wait for agent_end
            deadline = time.time() + 30
            while time.time() < deadline:
                if any(e.event_type == "code_agent_end" for e in collected):
                    break
                time.sleep(0.2)

            event_types = [e.event_type for e in collected]
            assert "code_agent_start" in event_types
            assert "code_agent_end" in event_types
            assert "code_text_delta" in event_types or "code_text_end" in event_types

            # Check text content
            text_parts = [
                e.data.get("delta", "")
                for e in collected
                if e.event_type == "code_text_delta"
            ]
            full_text = "".join(text_parts).lower()
            assert "integration" in full_text or "test" in full_text or "passed" in full_text

        finally:
            bridge.stop()
            assert not bridge.running
