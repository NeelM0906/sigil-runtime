"""Pi Coding Agent RPC bridge for Mission Control Code tab.

Manages a long-lived Pi subprocess communicating via JSONL over stdin/stdout
pipes (RPC mode). Supports multi-turn sessions, streaming events, and tool
call observation.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PiMessage:
    """A single message in a coding session."""
    role: str           # "user" or "assistant"
    content: str        # text content
    tools: list = field(default_factory=list)  # [{name, args, result}]
    timestamp: float = field(default_factory=time.time)


@dataclass
class PiSession:
    """Tracks one logical coding session inside the Pi process."""
    id: str
    title: str
    workspace_root: str
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    is_streaming: bool = False
    last_activity: float = field(default_factory=time.time)
    messages: list = field(default_factory=list)  # list[PiMessage]
    _current_text: str = ""       # accumulates streaming text for current turn
    _current_tools: list = field(default_factory=list)  # accumulates tool calls for current turn


@dataclass
class PiEvent:
    """Normalised event emitted by the bridge for consumers (SSE fan-out)."""
    session_id: str
    event_type: str       # code_text_delta, code_text_end, code_tool_start, ...
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PI_MODEL = "openrouter/anthropic/claude-sonnet-4"
DEFAULT_TOOLS = "read,bash,edit,write,grep,find,ls"
CRASH_WINDOW_S = 60
CRASH_MAX = 3
CRASH_COOLDOWN_S = 120

# Map Pi assistantMessageEvent types → MC event types
_EVENT_MAP = {
    "text_start":     "code_text_start",
    "text_delta":     "code_text_delta",
    "text_end":       "code_text_end",
    "toolcall_start": "code_tool_call_start",
    "toolcall_delta": "code_tool_call_delta",
    "toolcall_end":   "code_tool_call_end",
    "thinking_start": "code_thinking_start",
    "thinking_delta": "code_thinking_delta",
    "thinking_end":   "code_thinking_end",
}


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class PiBridge:
    """Manages a Pi coding agent subprocess and exposes a session-oriented API.

    Lifecycle:
        bridge = PiBridge(workspace_root="/path/to/project")
        bridge.start()
        bridge.send_prompt(session_id, "Fix the login bug")
        # ... consume events via bridge.subscribe() ...
        bridge.stop()
    """

    # Identity files to inject as system prompt (SAI Prime persona)
    _IDENTITY_FILES = ("SOUL.md", "IDENTITY.md", "MISSION.md")

    def __init__(
        self,
        workspace_root: str | Path,
        model: str = DEFAULT_PI_MODEL,
        tools: str = DEFAULT_TOOLS,
        thinking: str = "off",
        session_dir: str | None = None,
        env_file: str | Path | None = None,
        on_event: Callable[[PiEvent], None] | None = None,
        identity_enabled: bool = True,
    ):
        self.workspace_root = str(workspace_root)
        self.model = model
        self.tools = tools
        self.thinking = thinking
        self.session_dir = session_dir
        self.env_file = str(env_file) if env_file else None
        self.identity_enabled = identity_enabled
        self._on_event = on_event

        self._proc: subprocess.Popen | None = None
        self._lock = threading.RLock()
        self._reader_thread: threading.Thread | None = None
        self._stop = threading.Event()

        # Session tracking
        self._sessions: dict[str, PiSession] = {}
        self._active_session_id: str | None = None
        self._active_workspace: str = str(workspace_root)  # current Pi process workspace

        # Event subscribers: id → Queue
        self._subscribers: dict[str, queue.Queue[PiEvent]] = {}
        self._sub_lock = threading.Lock()

        # Crash recovery state
        self._crash_times: list[float] = []
        self._cooldown_until: float = 0.0

        # Pending command responses: correlation id → Event+result
        self._pending: dict[str, tuple[threading.Event, dict]] = {}
        self._pending_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn the Pi RPC subprocess."""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return  # already running
            self._spawn()

    def stop(self) -> None:
        """Gracefully stop the Pi subprocess."""
        self._stop.set()
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc and proc.poll() is None:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=3)

    @property
    def running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def health(self) -> dict:
        """Return health status dict."""
        return {
            "running": self.running,
            "model": self.model,
            "workspace_root": self.workspace_root,
            "active_session": self._active_session_id,
            "session_count": len(self._sessions),
            "subscriber_count": len(self._subscribers),
        }

    def ensure_running(self) -> None:
        """Start if not running, with crash-storm protection."""
        if self.running:
            return
        now = time.time()
        if now < self._cooldown_until:
            raise RuntimeError(
                f"Pi bridge in crash cooldown until {self._cooldown_until:.0f} "
                f"({self._cooldown_until - now:.0f}s remaining)"
            )
        self._crash_times = [t for t in self._crash_times if now - t < CRASH_WINDOW_S]
        if len(self._crash_times) >= CRASH_MAX:
            self._cooldown_until = now + CRASH_COOLDOWN_S
            raise RuntimeError(
                f"Pi crashed {CRASH_MAX} times in {CRASH_WINDOW_S}s, "
                f"cooldown for {CRASH_COOLDOWN_S}s"
            )
        self.start()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, title: str = "New session", workspace_root: str | None = None) -> PiSession:
        """Create a new logical session.

        If *workspace_root* differs from the running Pi's workspace, Pi is
        restarted with the new cwd so file operations target the right folder.
        """
        ws = workspace_root or self.workspace_root
        # Resolve and validate
        ws_path = Path(ws).expanduser().resolve()
        if not ws_path.is_dir():
            raise ValueError(f"Workspace not found: {ws}")
        ws = str(ws_path)

        # If workspace changed, restart Pi with new cwd
        if self.running and ws != self._active_workspace:
            log.info("Workspace changed: %s → %s, restarting Pi", self._active_workspace, ws)
            self.stop()

        self._active_workspace = ws
        self.ensure_running()

        sid = f"code-{uuid.uuid4().hex[:12]}"
        session = PiSession(
            id=sid,
            title=title,
            workspace_root=ws,
        )
        self._sessions[sid] = session

        # If there was a previous active session in the same Pi process, reset context
        if self._active_session_id is not None:
            self._send_command({"type": "new_session"})

        self._active_session_id = sid
        return session

    def list_sessions(self) -> list[dict]:
        return [
            {
                "id": s.id,
                "title": s.title,
                "workspace_root": s.workspace_root,
                "created_at": s.created_at,
                "message_count": s.message_count,
                "is_streaming": s.is_streaming,
                "last_activity": s.last_activity,
            }
            for s in sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)
        ]

    def get_session(self, session_id: str) -> PiSession | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------

    def send_prompt(self, session_id: str, message: str) -> dict:
        """Send a user prompt to the Pi agent for the given session."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")

        # Restart Pi if session targets a different workspace
        if session.workspace_root != self._active_workspace:
            log.info("Session workspace differs, restarting Pi: %s", session.workspace_root)
            self.stop()
            self._active_workspace = session.workspace_root

        self.ensure_running()

        # Switch active session if needed
        if self._active_session_id != session_id:
            self._send_command({"type": "new_session"})
            self._active_session_id = session_id

        session.message_count += 1
        session.is_streaming = True
        session.last_activity = time.time()
        session._current_text = ""
        session._current_tools = []
        # Record user message
        session.messages.append(PiMessage(role="user", content=message))

        resp = self._send_command({
            "type": "prompt",
            "message": message,
        })
        return resp

    def abort(self, session_id: str) -> dict:
        """Abort the current agent operation."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")
        resp = self._send_command({"type": "abort"})
        session.is_streaming = False
        return resp

    def get_messages(self, session_id: str) -> dict:
        """Retrieve conversation messages from local session history."""
        session = self._sessions.get(session_id)
        if not session:
            return {"messages": []}
        return {
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "tools": m.tools,
                    "timestamp": m.timestamp,
                }
                for m in session.messages
            ],
        }

    def get_state(self) -> dict:
        """Get current Pi agent state."""
        return self._send_command({"type": "get_state"}, timeout=5)

    # ------------------------------------------------------------------
    # Extension UI (approval flow)
    # ------------------------------------------------------------------

    def respond_ui(self, request_id: str, response: dict) -> None:
        """Send an extension_ui_response to Pi (for approval dialogs).

        ``response`` should be one of:
        - ``{"value": "Allow"}`` for select dialogs
        - ``{"confirmed": True}`` for confirm dialogs
        - ``{"cancelled": True}`` to dismiss
        """
        msg = {"type": "extension_ui_response", "id": request_id, **response}
        with self._lock:
            proc = self._proc
        if not proc or proc.poll() is not None:
            raise RuntimeError("Pi process is not running")
        try:
            raw = json.dumps(msg) + "\n"
            proc.stdin.write(raw)
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError(f"Failed to write UI response: {exc}") from exc

    # ------------------------------------------------------------------
    # Event subscription
    # ------------------------------------------------------------------

    def subscribe(self, session_id: str | None = None, max_size: int = 500) -> tuple[str, queue.Queue[PiEvent]]:
        """Subscribe to Pi events. Returns (subscription_id, queue).

        If session_id is provided, only events for that session are delivered.
        """
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        q: queue.Queue[PiEvent] = queue.Queue(maxsize=max_size)
        with self._sub_lock:
            self._subscribers[sub_id] = q
        return sub_id, q

    def unsubscribe(self, sub_id: str) -> None:
        with self._sub_lock:
            self._subscribers.pop(sub_id, None)

    # ------------------------------------------------------------------
    # Internal: subprocess management
    # ------------------------------------------------------------------

    def _spawn(self) -> None:
        """Spawn the Pi RPC process."""
        env = os.environ.copy()

        # Load API key from project .env if available
        if self.env_file and Path(self.env_file).is_file():
            for line in Path(self.env_file).read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in env:
                        env[key] = val

        cmd = [
            "pi",
            "--mode", "rpc",
            "--thinking", self.thinking,
            "--model", self.model,
            "--tools", self.tools,
        ]
        if self.session_dir:
            cmd.extend(["--session-dir", self.session_dir])
        else:
            cmd.append("--no-session")

        # Inject SAI identity as appended system prompt
        if self.identity_enabled:
            identity_text = self._load_identity()
            if identity_text:
                cmd.extend(["--append-system-prompt", identity_text])
                log.info("Pi identity loaded (%d chars from %s)", len(identity_text), ", ".join(self._IDENTITY_FILES))

        cwd = self._active_workspace
        log.info("Starting Pi RPC: %s (cwd=%s)", " ".join(cmd[:8]) + "...", cwd)

        self._stop.clear()
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env,
        )

        self._reader_thread = threading.Thread(
            target=self._read_loop, name="pi-rpc-reader", daemon=True
        )
        self._reader_thread.start()

        # Also drain stderr in background
        threading.Thread(
            target=self._drain_stderr, name="pi-rpc-stderr", daemon=True
        ).start()

    def _read_loop(self) -> None:
        """Read JSONL events from Pi stdout and dispatch."""
        proc = self._proc
        if not proc or not proc.stdout:
            return
        try:
            for raw_line in proc.stdout:
                if self._stop.is_set():
                    break
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("Pi RPC: non-JSON line: %s", line[:200])
                    continue
                self._dispatch_event(obj)
        except Exception:
            if not self._stop.is_set():
                log.exception("Pi RPC reader error")
        finally:
            # Process exited or pipe closed
            if not self._stop.is_set():
                self._crash_times.append(time.time())
                log.warning("Pi RPC process exited unexpectedly")
                # Mark all sessions as not streaming
                for s in self._sessions.values():
                    s.is_streaming = False

    def _load_identity(self) -> str:
        """Load SAI identity files from workspace to use as system prompt."""
        ws = Path(self.workspace_root)
        # Look in workspaces/prime/ first, then workspace root
        search_dirs = [ws / "workspaces" / "prime", ws]
        parts = []
        for identity_file in self._IDENTITY_FILES:
            for d in search_dirs:
                p = d / identity_file
                if p.is_file():
                    try:
                        text = p.read_text(encoding="utf-8").strip()
                        if text:
                            parts.append(text)
                    except OSError:
                        pass
                    break  # found this file, move to next
        return "\n\n".join(parts) if parts else ""

    def _drain_stderr(self) -> None:
        """Log stderr output from Pi."""
        proc = self._proc
        if not proc or not proc.stderr:
            return
        try:
            for line in proc.stderr:
                if self._stop.is_set():
                    break
                line = line.strip()
                if line:
                    log.debug("Pi stderr: %s", line[:500])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal: command send / response correlation
    # ------------------------------------------------------------------

    def _send_command(self, cmd: dict, timeout: float = 30) -> dict:
        """Send a command to Pi stdin and wait for the response."""
        with self._lock:
            proc = self._proc
        if not proc or proc.poll() is not None:
            raise RuntimeError("Pi process is not running")

        # Add correlation ID
        cmd_id = f"cmd-{uuid.uuid4().hex[:8]}"
        cmd["id"] = cmd_id

        evt = threading.Event()
        result: dict = {}
        with self._pending_lock:
            self._pending[cmd_id] = (evt, result)

        try:
            raw = json.dumps(cmd) + "\n"
            proc.stdin.write(raw)
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            with self._pending_lock:
                self._pending.pop(cmd_id, None)
            raise RuntimeError(f"Failed to write to Pi stdin: {exc}") from exc

        if not evt.wait(timeout=timeout):
            with self._pending_lock:
                self._pending.pop(cmd_id, None)
            return {"success": False, "error": "timeout", "command": cmd.get("type")}

        with self._pending_lock:
            self._pending.pop(cmd_id, None)

        return result

    # ------------------------------------------------------------------
    # Internal: event dispatch
    # ------------------------------------------------------------------

    def _dispatch_event(self, obj: dict) -> None:
        """Route a parsed JSONL event from Pi."""
        event_type = obj.get("type", "")

        # Command response correlation
        if event_type == "response":
            cmd_id = obj.get("id")
            if cmd_id:
                with self._pending_lock:
                    pending = self._pending.get(cmd_id)
                if pending:
                    evt, result_ref = pending
                    result_ref.update(obj)
                    evt.set()
                    return
            # Response without correlation ID — still useful
            # (e.g., initial response to prompt)
            return

        session_id = self._active_session_id or "unknown"
        session = self._sessions.get(session_id)

        # Extension UI requests (approval flow)
        if event_type == "extension_ui_request":
            method = obj.get("method", "")
            req_id = obj.get("id", "")
            # Dialog methods that need a response
            if method in ("select", "confirm", "input", "editor"):
                self._emit(PiEvent(session_id, "code_approval_required", {
                    "request_id": req_id,
                    "method": method,
                    "title": obj.get("title", ""),
                    "message": obj.get("message", ""),
                    "options": obj.get("options", []),
                    "timeout": obj.get("timeout"),
                }))
            # Fire-and-forget: notify, setStatus, etc.
            elif method in ("notify", "setStatus"):
                self._emit(PiEvent(session_id, "code_notification", {
                    "method": method,
                    "title": obj.get("title", ""),
                    "message": obj.get("message", ""),
                    "level": obj.get("level", "info"),
                }))
            return

        # Agent lifecycle events
        if event_type == "agent_start":
            if session:
                session.is_streaming = True
                session._current_text = ""
                session._current_tools = []
            self._emit(PiEvent(session_id, "code_agent_start"))
            return

        if event_type == "agent_end":
            if session:
                session.is_streaming = False
                # Save accumulated assistant message
                if session._current_text or session._current_tools:
                    session.messages.append(PiMessage(
                        role="assistant",
                        content=session._current_text,
                        tools=list(session._current_tools),
                    ))
                    session.message_count += 1
                    session._current_text = ""
                    session._current_tools = []
            self._emit(PiEvent(session_id, "code_agent_end"))
            return

        if event_type in ("turn_start", "turn_end"):
            self._emit(PiEvent(session_id, f"code_{event_type}"))
            return

        if event_type in ("message_start", "message_end"):
            msg = obj.get("message", {})
            role = msg.get("role", "")
            pi_event = PiEvent(session_id, f"code_{event_type}", {
                "role": role,
            })
            # On assistant message_end, extract final content
            if event_type == "message_end" and role == "assistant":
                content = msg.get("content", [])
                text_parts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "tool": block.get("name", ""),
                                "id": block.get("id", ""),
                            })
                pi_event.data["text"] = "\n".join(text_parts)
                pi_event.data["tool_calls"] = tool_calls
                # Usage info
                usage = msg.get("usage", {})
                if usage:
                    pi_event.data["usage"] = {
                        "input_tokens": usage.get("input", 0),
                        "output_tokens": usage.get("output", 0),
                        "cache_read": usage.get("cacheRead", 0),
                        "total_tokens": usage.get("totalTokens", 0),
                        "cost": usage.get("cost", {}).get("total", 0),
                    }
                if session:
                    session.last_activity = time.time()
            self._emit(pi_event)
            return

        # Tool execution lifecycle (top-level events)
        if event_type in ("tool_execution_start", "tool_execution_end"):
            mc_type = "code_tool_exec_start" if "start" in event_type else "code_tool_exec_end"
            data: dict[str, Any] = {}
            if "tool" in obj:
                data["tool"] = obj["tool"]
            if "toolName" in obj:
                data["tool_name"] = obj["toolName"]
            if "result" in obj:
                result_str = str(obj["result"])
                data["result_preview"] = result_str[:2000]
                # Attach result to last tool call in session
                if session and event_type == "tool_execution_end" and session._current_tools:
                    session._current_tools[-1]["result"] = result_str[:2000]
            self._emit(PiEvent(session_id, mc_type, data))
            return

        # Streaming assistant message updates
        if event_type == "message_update":
            assistant_evt = obj.get("assistantMessageEvent", {})
            atype = assistant_evt.get("type", "")
            mc_type = _EVENT_MAP.get(atype)
            if not mc_type:
                return  # unmapped event, skip

            data = {}
            if atype == "text_delta":
                data["delta"] = assistant_evt.get("delta", "")
                if session:
                    session._current_text += data["delta"]
            elif atype == "text_end":
                data["content"] = assistant_evt.get("content", "")
            elif atype == "text_start":
                pass  # just a signal
            elif atype == "toolcall_start":
                # Tool name can be in toolName or nested in partial.content[].name
                tool_name = assistant_evt.get("toolName", "")
                if not tool_name:
                    for block in assistant_evt.get("partial", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "toolCall":
                            tool_name = block.get("name", "")
                            break
                data["tool_name"] = tool_name
                data["tool_call_id"] = assistant_evt.get("toolCallId", "")
            elif atype == "toolcall_delta":
                data["delta"] = assistant_evt.get("delta", "")
            elif atype == "toolcall_end":
                tool_name = assistant_evt.get("toolName", "")
                args_str = assistant_evt.get("arguments", "")
                if not tool_name or not args_str:
                    for block in assistant_evt.get("partial", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "toolCall":
                            tool_name = tool_name or block.get("name", "")
                            if not args_str:
                                raw_args = block.get("arguments", {})
                                args_str = json.dumps(raw_args) if isinstance(raw_args, dict) else str(raw_args)
                            break
                data["tool_name"] = tool_name
                data["arguments"] = args_str
                if session:
                    session._current_tools.append({
                        "name": tool_name,
                        "args": args_str,
                    })
            elif atype == "thinking_delta":
                data["delta"] = assistant_evt.get("delta", "")
            elif atype == "thinking_end":
                data["content"] = assistant_evt.get("content", "")

            self._emit(PiEvent(session_id, mc_type, data))
            return

    # ------------------------------------------------------------------
    # File browsing (workspace filesystem)
    # ------------------------------------------------------------------

    # Directories to skip in file tree
    _SKIP_DIRS = frozenset({
        ".git", ".venv", "__pycache__", "node_modules", ".runtime",
        ".pytest_cache", "dist", "build", ".mypy_cache", ".ruff_cache",
        ".pi", ".openclaw", ".portable-home", "portable-openclaw",
    })

    def file_tree(self, max_depth: int = 3, workspace: str | None = None) -> list[dict]:
        """Return a file/dir tree of the workspace for the sidebar."""
        root = Path(workspace or self._active_workspace)
        if not root.is_dir():
            return []
        return self._scan_dir(root, root, 0, max_depth)

    def _scan_dir(self, base: Path, directory: Path, depth: int, max_depth: int) -> list[dict]:
        if depth > max_depth:
            return []
        entries: list[dict] = []
        try:
            items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return []
        for item in items:
            name = item.name
            if name.startswith(".") and depth == 0:
                continue
            if item.is_dir():
                if name in self._SKIP_DIRS:
                    continue
                children = self._scan_dir(base, item, depth + 1, max_depth) if depth < max_depth else []
                entries.append({
                    "name": name,
                    "type": "dir",
                    "path": str(item.relative_to(base)),
                    "children": children,
                })
            elif item.is_file():
                try:
                    size = item.stat().st_size
                except OSError:
                    size = 0
                entries.append({
                    "name": name,
                    "type": "file",
                    "path": str(item.relative_to(base)),
                    "size": size,
                })
        return entries

    def read_file(self, rel_path: str, max_bytes: int = 100_000, workspace: str | None = None) -> dict:
        """Read a file from the workspace. Returns {content, path, size, truncated}."""
        root = Path(workspace or self._active_workspace)
        target = (root / rel_path).resolve()
        # Path traversal guard
        if not str(target).startswith(str(root.resolve())):
            raise ValueError("Path traversal not allowed")
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {rel_path}")
        size = target.stat().st_size
        truncated = size > max_bytes
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if truncated:
                content = content[:max_bytes]
        except UnicodeDecodeError:
            content = f"[Binary file, {size} bytes]"
        return {
            "path": rel_path,
            "content": content,
            "size": size,
            "truncated": truncated,
        }

    def _emit(self, event: PiEvent) -> None:
        """Fan out event to subscribers and optional callback."""
        # Callback (for dashboard SSE integration)
        if self._on_event:
            try:
                self._on_event(event)
            except Exception:
                log.exception("Pi event callback error")

        # Queue-based subscribers
        with self._sub_lock:
            dead: list[str] = []
            for sub_id, q in self._subscribers.items():
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(sub_id)
            for sub_id in dead:
                self._subscribers.pop(sub_id, None)
