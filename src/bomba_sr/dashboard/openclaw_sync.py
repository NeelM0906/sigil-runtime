from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.openclaw.integration import bundled_openclaw_root, load_openclaw_config, portable_display_path, sanitize_portable_text
from bomba_sr.storage.db import dict_from_row


log = logging.getLogger(__name__)

MC_TENANT = "tenant-local"
MC_PROJECT_ID = "mc-project"

AGENT_TO_BEING_ID = {
    "main": "prime",
    "forge": "forge",
    "scholar": "scholar",
    "memory": "sai-memory",
    "recovery": "recovery",
}

AGENT_DEFAULTS = {
    "main": {
        "name": "SAI",
        "avatar": "🔥",
        "color": "#F97316",
        "type": "runtime",
        "role": "Primary OpenClaw runtime",
    },
    "forge": {
        "name": "Sai Forge",
        "avatar": "⚔️",
        "color": "#EF4444",
        "type": "sister",
        "role": "Creative/build execution sister",
    },
    "scholar": {
        "name": "Sai Scholar",
        "avatar": "📚",
        "color": "#3B82F6",
        "type": "sister",
        "role": "Research and synthesis sister",
    },
    "memory": {
        "name": "SAI Memory",
        "avatar": "🧠",
        "color": "#8B5CF6",
        "type": "sister",
        "role": "Memory and continuity sister",
    },
    "recovery": {
        "name": "Sai Recovery",
        "avatar": "🌱",
        "color": "#10B981",
        "type": "sister",
        "role": "Recovery and revenue sister",
    },
}


@dataclass
class ImportedMessage:
    id: str
    sender: str
    content: str
    timestamp: str
    msg_type: str = "direct"
    mode: str = "auto"
    task_ref: str | None = None


@dataclass
class ImportedSession:
    session_id: str
    agent_id: str
    being_id: str
    source_key: str
    session_file: Path
    updated_at: str
    updated_at_epoch_ms: int
    created_at: str
    name: str
    task_title: str
    task_status: str
    priority: str
    route_kind: str
    messages: list[ImportedMessage]


class OpenClawSync:
    """Continuously mirror a live .openclaw install into Mission Control."""

    def __init__(
        self,
        dashboard_svc: Any,
        db: Any,
        project_service: Any,
        openclaw_root: Path | None = None,
    ):
        self.dashboard = dashboard_svc
        self.db = db
        self.project_service = project_service
        self.root = openclaw_root or self._discover_root()
        self.session_limit = max(1, int(os.getenv("BOMBA_OPENCLAW_SYNC_LIMIT", "120")))
        self.message_limit = max(10, int(os.getenv("BOMBA_OPENCLAW_SYNC_MESSAGES", "160")))
        self.active_window_seconds = max(60, int(os.getenv("BOMBA_OPENCLAW_ACTIVE_WINDOW_SECONDS", "1800")))
        self.poll_seconds = max(0.0, float(os.getenv("BOMBA_OPENCLAW_SYNC_POLL_SECONDS", "3")))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._sync_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.root is not None and self.root.is_dir() and (self.root / "openclaw.json").is_file()

    def start(self) -> None:
        if not self.enabled:
            return
        self.sync_once()
        if self.poll_seconds <= 0:
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="openclaw-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def sync_once(self) -> None:
        if not self.enabled:
            return
        if not self._sync_lock.acquire(blocking=False):
            return
        try:
            config = self._load_config()
            sessions = self._collect_sessions()
            self._sync_beings(config, sessions)
            self._sync_sessions(sessions)
            self._sync_tasks(sessions)
        except Exception:
            log.exception("OpenClaw sync failed")
        finally:
            self._sync_lock.release()

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            self.sync_once()

    def _discover_root(self) -> Path | None:
        explicit = os.getenv("BOMBA_OPENCLAW_SOURCE_ROOT", "").strip()
        if explicit:
            return Path(explicit).expanduser().resolve()
        bundled_root = bundled_openclaw_root()
        if (bundled_root / "openclaw.json").is_file():
            return bundled_root
        candidate = Path(__file__).resolve().parents[4]
        if (candidate / "openclaw.json").is_file():
            return candidate
        return None

    def _load_config(self) -> dict[str, Any]:
        return load_openclaw_config(self.root)

    def _collect_sessions(self) -> list[ImportedSession]:
        assert self.root is not None
        collected: list[ImportedSession] = []
        for agent_id, being_id in AGENT_TO_BEING_ID.items():
            sessions_dir = self.root / "agents" / agent_id / "sessions"
            sessions_index = sessions_dir / "sessions.json"
            if not sessions_index.is_file():
                continue
            try:
                entries = json.loads(sessions_index.read_text(encoding="utf-8"))
            except Exception:
                log.debug("Failed to parse %s", sessions_index)
                continue
            for source_key, meta in entries.items():
                session_id = str(meta.get("sessionId") or "").strip()
                if not session_id:
                    continue
                session_file = self._resolve_session_file(sessions_dir, session_id)
                if session_file is None:
                    continue
                updated_ms = int(meta.get("updatedAt") or 0)
                imported = self._parse_session(
                    agent_id=agent_id,
                    being_id=being_id,
                    source_key=source_key,
                    session_id=session_id,
                    session_file=session_file,
                    updated_at_ms=updated_ms,
                )
                if imported is not None:
                    collected.append(imported)
        collected.sort(key=lambda item: item.updated_at_epoch_ms, reverse=True)
        return collected[: self.session_limit]

    def _resolve_session_file(self, sessions_dir: Path, session_id: str) -> Path | None:
        direct = sessions_dir / f"{session_id}.jsonl"
        if direct.is_file():
            return direct
        matches = sorted(sessions_dir.glob(f"{session_id}*.jsonl"))
        return matches[0] if matches else None

    def _parse_session(
        self,
        agent_id: str,
        being_id: str,
        source_key: str,
        session_id: str,
        session_file: Path,
        updated_at_ms: int,
    ) -> ImportedSession | None:
        messages: list[ImportedMessage] = []
        created_at = None
        first_user_text = ""
        try:
            lines = session_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        for idx, raw in enumerate(lines, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "session":
                created_at = self._coerce_iso(evt.get("timestamp")) or created_at
                continue
            if evt.get("type") != "message":
                continue
            msg = evt.get("message") or {}
            role = str(msg.get("role") or "")
            text = self._extract_message_text(role, msg)
            if not text:
                continue
            timestamp = self._coerce_iso(evt.get("timestamp") or msg.get("timestamp")) or self._now()
            if role == "user" and not first_user_text:
                first_user_text = text
            sender, msg_type = self._sender_for_role(role, being_id)
            messages.append(
                ImportedMessage(
                    id=self._stable_id(f"{session_file}:{idx}:{role}"),
                    sender=sender,
                    content=text,
                    timestamp=timestamp,
                    msg_type=msg_type,
                )
            )
        if not messages:
            return None
        messages = messages[-self.message_limit :]
        created_at = created_at or messages[0].timestamp
        if updated_at_ms <= 0:
            updated_at_ms = int(datetime.fromisoformat(messages[-1].timestamp.replace("Z", "+00:00")).timestamp() * 1000)
        updated_at = self._iso_from_epoch_ms(updated_at_ms)
        route_kind = self._route_kind(source_key)
        label = self._session_label(source_key, first_user_text)
        return ImportedSession(
            session_id=session_id,
            agent_id=agent_id,
            being_id=being_id,
            source_key=source_key,
            session_file=session_file,
            updated_at=updated_at,
            updated_at_epoch_ms=updated_at_ms,
            created_at=created_at,
            name=label,
            task_title=self._task_title(first_user_text, label),
            task_status=self._task_status(route_kind, updated_at_ms),
            priority=self._priority_for_route(route_kind),
            route_kind=route_kind,
            messages=messages,
        )

    def _sync_beings(self, config: dict[str, Any], sessions: list[ImportedSession]) -> None:
        active_by_being: dict[str, bool] = {}
        for session in sessions:
            if session.task_status == "in_progress":
                active_by_being[session.being_id] = True

        agents_by_id = {
            str(item.get("id")): item
            for item in (config.get("agents", {}) or {}).get("list", [])
            if isinstance(item, dict) and item.get("id")
        }
        now = self.dashboard._now()
        for agent_id, being_id in AGENT_TO_BEING_ID.items():
            meta = AGENT_DEFAULTS[agent_id]
            cfg = agents_by_id.get(agent_id, {})
            workspace = self._workspace_for_agent(agent_id, cfg)
            model = cfg.get("model", {})
            model_id = model.get("primary") if isinstance(model, dict) else str(model or "")
            raw_tools = ((cfg.get("tools") or {}).get("alsoAllow") if isinstance(cfg.get("tools"), dict) else None) or []
            tools = [tool for tool in raw_tools if isinstance(tool, str) and tool.strip()]
            being = self.dashboard.get_being(being_id) or {}
            payload = {
                "id": being_id,
                "name": being.get("name") or meta["name"],
                "role": meta["role"],
                "avatar": being.get("avatar") or meta["avatar"],
                "status": "busy" if active_by_being.get(being_id) else "online",
                "description": meta["role"],
                "type": being.get("type") or meta["type"],
                "tools": tools or being.get("tools", []),
                "skills": being.get("skills", []),
                "color": being.get("color") or meta["color"],
                "model_id": model_id,
                "workspace": workspace,
                "tenant_id": f"tenant-openclaw-{agent_id}",
                "auto_start": True if agent_id == "main" else being.get("auto_start", False),
            }
            self.dashboard._upsert_being(payload, now)
            self.dashboard._emit_event("being_status", {"being_id": being_id, "status": payload["status"]})

    def _workspace_for_agent(self, agent_id: str, cfg: dict[str, Any]) -> str:
        assert self.root is not None
        bundled = self.root.resolve() == bundled_openclaw_root(self.root).resolve()
        # For "main", prefer the workspace subdir (symlink to workspaces/prime)
        # so identity/memory files are read from the actual workspace, not the
        # portable-openclaw root.
        main_ws = self.root / "workspace"
        if not main_ws.exists():
            main_ws = self.root
        default_map = {
            "main": main_ws,
            "forge": self.root / "workspace-forge",
            "scholar": self.root / "workspace-scholar",
            "memory": self.root / "workspace-memory",
            "recovery": self.root / "workspace" / "sisters" / "sai-recovery",
        }
        raw = str(cfg.get("workspace") or "").strip()
        if raw and not bundled and agent_id != "main":
            return portable_display_path(Path(raw).expanduser().resolve(), self.root)
        return portable_display_path(default_map.get(agent_id, self.root / f"workspace-{agent_id}").resolve(), self.root)

    def _sync_sessions(self, sessions: list[ImportedSession]) -> None:
        for session in sessions:
            self._upsert_session_row(session)
            for message in session.messages:
                self._upsert_message_row(session, message)

    def _sync_tasks(self, sessions: list[ImportedSession]) -> None:
        for session in sessions:
            task_id = self._task_id_for_session(session.session_id)
            existing = self.db.execute(
                "SELECT * FROM project_tasks WHERE tenant_id = ? AND task_id = ?",
                (MC_TENANT, task_id),
            ).fetchone()
            task_payload = {
                "id": self._stable_id(f"task:{session.session_id}")[:24],
                "tenant_id": MC_TENANT,
                "task_id": task_id,
                "project_id": MC_PROJECT_ID,
                "title": session.task_title,
                "description": f"Live OpenClaw session mirrored from {session.source_key}",
                "status": session.task_status,
                "priority": session.priority,
                "owner_agent_id": session.being_id,
                "parent_task_id": None,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
            changed = False
            with self.db.transaction() as conn:
                if existing is None:
                    conn.execute(
                        """INSERT INTO project_tasks
                           (id, tenant_id, task_id, project_id, title, description, status, priority,
                            owner_agent_id, parent_task_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            task_payload["id"],
                            task_payload["tenant_id"],
                            task_payload["task_id"],
                            task_payload["project_id"],
                            task_payload["title"],
                            task_payload["description"],
                            task_payload["status"],
                            task_payload["priority"],
                            task_payload["owner_agent_id"],
                            task_payload["parent_task_id"],
                            task_payload["created_at"],
                            task_payload["updated_at"],
                        ),
                    )
                    changed = True
                else:
                    current = dict_from_row(existing)
                    changed = any(
                        str(current.get(field) or "") != str(task_payload[field] or "")
                        for field in ("title", "description", "status", "priority", "owner_agent_id", "updated_at")
                    )
                    if changed:
                        conn.execute(
                            """UPDATE project_tasks
                               SET title = ?, description = ?, status = ?, priority = ?,
                                   owner_agent_id = ?, updated_at = ?
                               WHERE tenant_id = ? AND task_id = ?""",
                            (
                                task_payload["title"],
                                task_payload["description"],
                                task_payload["status"],
                                task_payload["priority"],
                                task_payload["owner_agent_id"],
                                task_payload["updated_at"],
                                MC_TENANT,
                                task_id,
                            ),
                        )
                conn.execute("DELETE FROM mc_task_assignments WHERE task_id = ?", (task_id,))
                conn.execute(
                    "INSERT OR IGNORE INTO mc_task_assignments (task_id, being_id) VALUES (?, ?)",
                    (task_id, session.being_id),
                )
            if changed:
                task = dict(task_payload)
                task["assignees"] = [session.being_id]
                self.dashboard._emit_event("task_update", {
                    "action": "updated" if existing else "created",
                    "task": self.dashboard._normalize_task(task),
                })

    def _upsert_session_row(self, session: ImportedSession) -> None:
        existing = self.db.execute(
            "SELECT * FROM mc_chat_sessions WHERE id = ?",
            (session.session_id,),
        ).fetchone()
        if existing is None:
            self.db.execute_commit(
                "INSERT OR IGNORE INTO mc_chat_sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session.session_id, session.name, session.created_at, session.updated_at),
            )
            existing = self.db.execute(
                "SELECT * FROM mc_chat_sessions WHERE id = ?",
                (session.session_id,),
            ).fetchone()
            if existing is not None and str(existing["updated_at"]) != session.updated_at:
                self.db.execute_commit(
                    "UPDATE mc_chat_sessions SET name = ?, updated_at = ? WHERE id = ?",
                    (session.name, session.updated_at, session.session_id),
                )
            self.dashboard._emit_event("chat_session", {
                "action": "created",
                "session": {
                    "id": session.session_id,
                    "name": session.name,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                },
            })
            return
        current = dict_from_row(existing)
        if current.get("name") != session.name or current.get("updated_at") != session.updated_at:
            self.db.execute_commit(
                "UPDATE mc_chat_sessions SET name = ?, updated_at = ? WHERE id = ?",
                (session.name, session.updated_at, session.session_id),
            )
            self.dashboard._emit_event("chat_session", {
                "action": "updated",
                "session": {
                    "id": session.session_id,
                    "name": session.name,
                    "created_at": current.get("created_at") or session.created_at,
                    "updated_at": session.updated_at,
                },
            })

    def _upsert_message_row(self, session: ImportedSession, message: ImportedMessage) -> None:
        cur = self.db.execute_commit(
            """INSERT OR IGNORE INTO mc_messages
               (id, type, sender, targets, content, timestamp, mode, task_ref, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.id,
                message.msg_type,
                message.sender,
                json.dumps([]),
                message.content,
                message.timestamp,
                message.mode,
                self._task_id_for_session(session.session_id),
                session.session_id,
            ),
        )
        if cur.rowcount == 0:
            return
        row = self.db.execute("SELECT * FROM mc_messages WHERE id = ?", (message.id,)).fetchone()
        self.dashboard._emit_event("chat_message", self.dashboard._message_row(row))

    def _route_kind(self, source_key: str) -> str:
        parts = source_key.split(":")
        return parts[2] if len(parts) > 2 else "main"

    def _priority_for_route(self, route_kind: str) -> str:
        if route_kind == "cron":
            return "low"
        if route_kind == "subagent":
            return "high"
        if route_kind in {"discord", "telegram"}:
            return "medium"
        return "high"

    def _task_status(self, route_kind: str, updated_at_ms: int) -> str:
        age_seconds = max(0, int(time.time()) - int(updated_at_ms / 1000))
        if age_seconds <= self.active_window_seconds:
            return "in_progress"
        if route_kind == "cron":
            return "done"
        return "done"

    def _session_label(self, source_key: str, first_user_text: str) -> str:
        parts = source_key.split(":")
        route_kind = parts[2] if len(parts) > 2 else "main"
        base = "OpenClaw"
        if route_kind == "main":
            base = "Main Workspace"
        elif route_kind == "discord" and len(parts) >= 5:
            base = f"Discord {parts[4]}"
        elif route_kind == "telegram" and len(parts) >= 5:
            base = f"Telegram {parts[4]}"
        elif route_kind == "cron" and len(parts) >= 4:
            base = f"Cron {parts[3][:8]}"
        elif route_kind == "subagent" and len(parts) >= 4:
            base = f"Subagent {parts[3][:8]}"
        excerpt = self._one_line(first_user_text, 48)
        return f"{base} · {excerpt}" if excerpt else base

    def _task_title(self, first_user_text: str, fallback: str) -> str:
        title = self._one_line(first_user_text, 88)
        return title or fallback

    def _sender_for_role(self, role: str, being_id: str) -> tuple[str, str]:
        if role == "user":
            return "user", "direct"
        if role == "toolResult":
            return being_id, "direct"
        return being_id, "direct"

    def _extract_message_text(self, role: str, message: dict[str, Any]) -> str:
        blocks = message.get("content") or []
        parts: list[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                txt = str(block.get("text") or "").strip()
                if txt:
                    parts.append(txt)
            elif btype == "toolCall":
                name = str(block.get("name") or "").strip()
                args = block.get("arguments")
                arg_preview = self._one_line(json.dumps(args, sort_keys=True), 180) if args else ""
                label = f"[tool] {name}"
                parts.append(f"{label} {arg_preview}".strip())
            elif btype == "thinking":
                continue
        text = "\n".join(part for part in parts if part).strip()
        if role == "toolResult" and not text:
            details = message.get("details") or {}
            aggregated = str(details.get("aggregated") or "").strip()
            if aggregated:
                text = aggregated
        return self._sanitize_paths(text)

    def _sanitize_paths(self, text: str) -> str:
        return sanitize_portable_text(text, self.root)

    def _task_id_for_session(self, session_id: str) -> str:
        return f"ocl-task-{session_id[:12]}"

    def _stable_id(self, raw: str) -> str:
        return "ocl-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]

    def _coerce_iso(self, value: Any) -> str | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return self._iso_from_epoch_ms(int(value * 1000))
            text = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return None

    def _iso_from_epoch_ms(self, value: int) -> str:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()

    def _one_line(self, text: str, limit: int) -> str:
        first = " ".join((text or "").strip().split())
        if len(first) <= limit:
            return first
        return first[: limit - 3].rstrip() + "..."

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
