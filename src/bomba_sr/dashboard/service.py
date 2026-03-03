"""Mission Control dashboard service.

Owns mc_* tables for beings registry, chat messages, task history,
and SSE event streaming.  Delegates to ProjectService for task CRUD
and RuntimeBridge for real LLM routing.
"""
from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.storage.db import RuntimeDB, dict_from_row


MC_TENANT = "tenant-local"
MC_PROJECT_ID = "mc-project"
MC_PROJECT_NAME = "Mission Control"

# Being types
TYPE_SISTER = "sister"
TYPE_RUNTIME = "runtime"       # Prime — the host runtime itself
TYPE_VOICE_AGENT = "voice"     # Bland.ai voice agents — not chat-routable
TYPE_SUBAGENT = "subagent"     # BD-PIP, BD-WC etc.

_BEING_COLS = (
    "id", "name", "role", "avatar", "status", "description", "type",
    "tools", "skills", "color", "model_id", "workspace", "tenant_id",
    "auto_start", "phone", "agent_id", "metrics", "created_at", "updated_at",
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class DashboardService:
    """Service layer for the Mission Control dashboard."""

    def __init__(
        self,
        db: RuntimeDB,
        bridge: Any | None = None,
        sisters: Any | None = None,
    ):
        self.db = db
        self.bridge = bridge
        self.sisters = sisters
        self._sse_clients: dict[str, queue.Queue] = {}
        self._sse_lock = threading.Lock()
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        self.db.script("""
            CREATE TABLE IF NOT EXISTS mc_beings (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              role TEXT,
              avatar TEXT,
              status TEXT NOT NULL DEFAULT 'offline',
              description TEXT,
              type TEXT,
              tools TEXT,
              skills TEXT,
              color TEXT,
              model_id TEXT,
              workspace TEXT,
              tenant_id TEXT,
              auto_start INTEGER DEFAULT 0,
              phone TEXT,
              agent_id TEXT,
              metrics TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mc_messages (
              id TEXT PRIMARY KEY,
              type TEXT NOT NULL DEFAULT 'broadcast',
              sender TEXT NOT NULL,
              targets TEXT,
              content TEXT NOT NULL,
              timestamp TEXT NOT NULL,
              mode TEXT DEFAULT 'auto',
              task_ref TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_mc_messages_ts
              ON mc_messages(timestamp DESC);

            CREATE TABLE IF NOT EXISTS mc_task_history (
              id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              action TEXT NOT NULL,
              details TEXT,
              timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mc_task_history_task
              ON mc_task_history(task_id, timestamp DESC);

            CREATE TABLE IF NOT EXISTS mc_task_assignments (
              task_id TEXT NOT NULL,
              being_id TEXT NOT NULL,
              PRIMARY KEY (task_id, being_id)
            );

            CREATE TABLE IF NOT EXISTS mc_events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mc_events_type
              ON mc_events(event_type, seq);
        """)
        self.db.commit()

    # ------------------------------------------------------------------
    # Beings
    # ------------------------------------------------------------------

    def seed_beings(self, json_path: str | Path) -> int:
        """Import beings from JSON seed file.  Skips if table is non-empty."""
        count = self.db.execute("SELECT COUNT(*) FROM mc_beings").fetchone()[0]
        if count > 0:
            return 0

        path = Path(json_path)
        if not path.exists():
            return 0
        data = json.loads(path.read_text())
        beings = data.get("beings", data) if isinstance(data, dict) else data

        now = self._now()
        inserted = 0
        for b in beings:
            self._upsert_being(b, now)
            inserted += 1
        self.db.commit()
        return inserted

    def load_beings_from_configs(self) -> int:
        """Load beings from real config files: sisters.json + SoulConfig + voice agents.

        This replaces the JSON seed approach with config-driven loading.
        Beings are upserted (existing records updated, new ones inserted).
        Returns the number of beings loaded.
        """
        beings: list[dict] = []

        # ── Tier 1: Prime (the host runtime) ─────────────────────
        prime_ws = _PROJECT_ROOT / "workspaces" / "prime"
        prime_soul = self._load_soul_safe(prime_ws)
        beings.append({
            "id": "prime",
            "name": "SAI",
            "role": "Primary being — holds the vision, coordinates all sisters",
            "avatar": prime_soul.emoji if prime_soul else "🔥",
            "status": "online",
            "description": "SAI (Super Actualized Intelligence). The primary being. Sisters are her extensions.",
            "type": TYPE_RUNTIME,
            "tools": [],
            "skills": ["orchestration", "delegation", "memory", "web_search"],
            "color": "#F97316",
            "model_id": "anthropic/claude-opus-4.6",
            "workspace": "workspaces/prime",
            "tenant_id": MC_TENANT,
            "auto_start": True,
        })

        # ── Tier 1: Sisters from sisters.json ─────────────────────
        sisters_json = _PROJECT_ROOT / "workspaces" / "prime" / "sisters.json"
        if sisters_json.exists():
            try:
                data = json.loads(sisters_json.read_text())
                for s in data.get("sisters", []):
                    ws_path = _PROJECT_ROOT / s["workspace_root"]
                    soul = self._load_soul_safe(ws_path)
                    beings.append({
                        "id": s["sister_id"],
                        "name": soul.name if soul else s["display_name"],
                        "role": s.get("role", ""),
                        "avatar": soul.emoji if soul else s.get("emoji", ""),
                        "status": "online",
                        "description": s.get("role", ""),
                        "type": TYPE_SISTER,
                        "tools": [],
                        "skills": [ct.get("name", "") for ct in s.get("cron_tasks", [])],
                        "color": self._color_for_sister(s["sister_id"]),
                        "model_id": s.get("model_id", ""),
                        "workspace": s["workspace_root"],
                        "tenant_id": s["tenant_id"],
                        "auto_start": s.get("auto_start", False),
                    })
            except (json.JSONDecodeError, KeyError, OSError):
                pass

        # ── Tier 1b: Recovery sub-agents (BD-PIP, BD-WC) ─────────
        bd_agents_dir = _PROJECT_ROOT / "workspaces" / "recovery" / "agents"
        if bd_agents_dir.is_dir():
            bd_configs = {
                "sai-bd-pip": {
                    "id": "bd-pip",
                    "color": "#EF4444",
                    "role": "PIP business development specialist",
                },
                "sai-bd-wc": {
                    "id": "bd-wc",
                    "color": "#F59E0B",
                    "role": "Workers comp business development specialist",
                },
            }
            for dirname, cfg in bd_configs.items():
                agent_dir = bd_agents_dir / dirname
                if not (agent_dir / "IDENTITY.md").exists():
                    continue
                soul = self._load_soul_safe(agent_dir)
                beings.append({
                    "id": cfg["id"],
                    "name": soul.name if soul else dirname.upper(),
                    "role": cfg["role"],
                    "avatar": soul.emoji if soul else "🎯",
                    "status": "offline",
                    "description": cfg["role"],
                    "type": TYPE_SUBAGENT,
                    "tools": [],
                    "skills": [],
                    "color": cfg["color"],
                    "model_id": "",
                    "workspace": f"workspaces/recovery/agents/{dirname}",
                    "tenant_id": "tenant-recovery",
                    "auto_start": False,
                })

        # ── Tier 2: Voice agents from Bland configs ───────────────
        configs_dir = _PROJECT_ROOT / "workspaces" / "prime" / "configs"
        if configs_dir.is_dir():
            voice_configs = {
                "callie-sean-config.json": {
                    "id": "callie",
                    "name": "Callie",
                    "avatar": "📞",
                    "color": "#EC4899",
                    "role": "Voice agent — Sean's dedicated Bland.ai assistant",
                },
                "athena-bella-hoi-config.json": {
                    "id": "athena-hoi",
                    "name": "Athena (HOI)",
                    "avatar": "🎙️",
                    "color": "#6366F1",
                    "role": "Voice agent — Heart of Influence Bella pathway",
                },
                "athena-leadership-config.json": {
                    "id": "athena-leadership",
                    "name": "Athena (Leadership)",
                    "avatar": "🎙️",
                    "color": "#7C3AED",
                    "role": "Voice agent — Leadership pathway",
                },
                "mylo-template.json": {
                    "id": "mylo",
                    "name": "Mylo",
                    "avatar": "🎤",
                    "color": "#14B8A6",
                    "role": "Voice agent — Template configuration",
                },
            }
            for filename, cfg in voice_configs.items():
                config_path = configs_dir / filename
                if not config_path.exists():
                    continue
                try:
                    bland_data = json.loads(config_path.read_text())
                    agent_block = bland_data.get("agent", bland_data)
                    agent_id = agent_block.get("agent_id", "")
                except (json.JSONDecodeError, OSError):
                    agent_id = ""

                beings.append({
                    "id": cfg["id"],
                    "name": cfg["name"],
                    "role": cfg["role"],
                    "avatar": cfg["avatar"],
                    "status": "offline",
                    "description": cfg["role"],
                    "type": TYPE_VOICE_AGENT,
                    "tools": [],
                    "skills": ["voice_call"],
                    "color": cfg["color"],
                    "model_id": "",
                    "workspace": "",
                    "tenant_id": "",
                    "auto_start": False,
                    "agent_id": agent_id,
                })

        # ── Upsert all beings ─────────────────────────────────────
        now = self._now()
        for b in beings:
            self._upsert_being(b, now)
        self.db.commit()
        return len(beings)

    def _upsert_being(self, b: dict, now: str) -> None:
        """Insert or update a being record."""
        existing = self.db.execute(
            "SELECT id FROM mc_beings WHERE id = ?", (b["id"],)
        ).fetchone()
        if existing:
            self.db.execute(
                """UPDATE mc_beings SET
                   name=?, role=?, avatar=?, description=?, type=?,
                   tools=?, skills=?, color=?, model_id=?, workspace=?,
                   tenant_id=?, auto_start=?, phone=?, agent_id=?,
                   updated_at=?
                   WHERE id=?""",
                (
                    b["name"], b.get("role"), b.get("avatar"),
                    b.get("description"), b.get("type"),
                    json.dumps(b.get("tools", [])),
                    json.dumps(b.get("skills", [])), b.get("color"),
                    b.get("model_id"), b.get("workspace"),
                    b.get("tenant_id"), 1 if b.get("auto_start") else 0,
                    b.get("phone"), b.get("agent_id"),
                    now, b["id"],
                ),
            )
        else:
            self.db.execute(
                """INSERT INTO mc_beings
                   (id,name,role,avatar,status,description,type,tools,skills,
                    color,model_id,workspace,tenant_id,auto_start,phone,
                    agent_id,metrics,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    b["id"], b["name"], b.get("role"), b.get("avatar"),
                    b.get("status", "offline"), b.get("description"),
                    b.get("type"), json.dumps(b.get("tools", [])),
                    json.dumps(b.get("skills", [])), b.get("color"),
                    b.get("model_id"), b.get("workspace"),
                    b.get("tenant_id"), 1 if b.get("auto_start") else 0,
                    b.get("phone"), b.get("agent_id"),
                    json.dumps(b.get("metrics", {})), now, now,
                ),
            )

    def list_beings(
        self,
        type_filter: str | None = None,
        status_filter: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM mc_beings WHERE 1=1"
        params: list[Any] = []
        if type_filter:
            sql += " AND type = ?"
            params.append(type_filter)
        if status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        sql += " ORDER BY name"
        rows = self.db.execute(sql, params).fetchall()
        return [self._being_row(r) for r in rows]

    def get_being(self, being_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM mc_beings WHERE id = ?", (being_id,)
        ).fetchone()
        return self._being_row(row) if row else None

    def update_being(self, being_id: str, changes: dict) -> dict | None:
        allowed = {
            "name", "role", "avatar", "status", "description",
            "tools", "skills", "color", "model_id", "metrics",
        }
        sets = []
        params: list[Any] = []
        for k, v in changes.items():
            if k not in allowed:
                continue
            if k in ("tools", "skills", "metrics"):
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            params.append(v)
        if not sets:
            return self.get_being(being_id)

        sets.append("updated_at = ?")
        params.append(self._now())
        params.append(being_id)

        self.db.execute(
            f"UPDATE mc_beings SET {', '.join(sets)} WHERE id = ?", params
        )
        self.db.commit()

        being = self.get_being(being_id)
        if being and "status" in changes:
            self._emit_event("being_status", {
                "being_id": being_id, "status": changes["status"],
            })
        return being

    def sync_being_statuses_from_sisters(self) -> None:
        """Update mc_beings status from SisterRegistry if available."""
        if not self.sisters:
            return
        try:
            sisters = self.sisters.list_sisters()
        except Exception:
            return
        for s in sisters:
            sid = s.get("sister_id") or s.get("id")
            status = "online" if s.get("running") else "offline"
            self.db.execute(
                "UPDATE mc_beings SET status = ?, updated_at = ? WHERE id = ?",
                (status, self._now(), sid),
            )
        self.db.commit()

    # ------------------------------------------------------------------
    # Chat messages
    # ------------------------------------------------------------------

    def list_messages(
        self,
        sender: str | None = None,
        target: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        sql = "SELECT * FROM mc_messages WHERE 1=1"
        params: list[Any] = []
        if sender:
            sql += " AND sender = ?"
            params.append(sender)
        if target:
            sql += " AND targets LIKE ?"
            params.append(f"%{target}%")
        if search:
            sql += " AND content LIKE ?"
            params.append(f"%{search}%")
        sql += " ORDER BY timestamp ASC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self.db.execute(sql, params).fetchall()
        return [self._message_row(r) for r in rows]

    def create_message(
        self,
        sender: str,
        content: str,
        targets: list[str] | None = None,
        msg_type: str = "broadcast",
        mode: str = "auto",
        task_ref: str | None = None,
    ) -> dict:
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        now = self._now()
        self.db.execute(
            """INSERT INTO mc_messages
               (id,type,sender,targets,content,timestamp,mode,task_ref)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                msg_id, msg_type, sender,
                json.dumps(targets or []),
                content, now, mode, task_ref,
            ),
        )
        self.db.commit()
        msg = self._message_row(
            self.db.execute(
                "SELECT * FROM mc_messages WHERE id = ?", (msg_id,)
            ).fetchone()
        )
        self._emit_event("chat_message", msg)
        return msg

    def create_system_message(
        self, content: str, task_ref: str | None = None
    ) -> dict:
        return self.create_message(
            sender="system", content=content,
            msg_type="system", task_ref=task_ref,
        )

    def delete_message(self, msg_id: str) -> bool:
        cur = self.db.execute(
            "DELETE FROM mc_messages WHERE id = ?", (msg_id,)
        )
        self.db.commit()
        return cur.rowcount > 0

    def route_to_being(self, being_id: str, content: str, sender: str = "user") -> None:
        """Route a message to a being via LLM in a background thread."""
        t = threading.Thread(
            target=self._route_to_being_sync,
            args=(being_id, content, sender),
            daemon=True,
        )
        t.start()

    def _route_to_being_sync(self, being_id: str, content: str, sender: str) -> None:
        """Call bridge.handle_turn for a being and store the response.

        Identity is loaded automatically by the bridge via SoulConfig from
        the being's workspace_root -- no identity prefix hack needed.
        """
        being = self.get_being(being_id) or {}
        being_type = being.get("type", "")

        # Voice agents are not chat-routable -- they use Bland.ai
        if being_type == TYPE_VOICE_AGENT:
            self.create_message(
                sender=being_id,
                content=f"[{being.get('name', being_id)} is a voice agent — use the Voice panel to trigger calls]",
                targets=[sender],
                msg_type="direct",
            )
            return

        # Offline beings cannot respond
        if being.get("status") == "offline":
            self.create_message(
                sender=being_id,
                content=f"[{being.get('name', being_id)} is currently offline and cannot respond.]",
                targets=[sender],
                msg_type="direct",
            )
            return

        if not self.bridge:
            self.create_message(
                sender=being_id,
                content=f"[{being_id} is offline — no LLM bridge available]",
                targets=[sender],
                msg_type="direct",
            )
            return

        tenant_id = being.get("tenant_id") or MC_TENANT
        session_id = f"mc-chat-{being_id}"

        # Resolve workspace: being's workspace relative to project root
        ws = being.get("workspace")
        if ws and ws != ".":
            workspace = str(_PROJECT_ROOT / ws)
        else:
            workspace = str(_PROJECT_ROOT)

        # Signal busy + typing before calling bridge
        self.update_being(being_id, {"status": "busy"})
        self._emit_event("being_typing", {
            "being_id": being_id,
            "being_name": being.get("name", being_id),
            "active": True,
        })

        try:
            from bomba_sr.runtime.bridge import TurnRequest
            req = TurnRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=sender,
                user_message=content,
                workspace_root=workspace,
            )
            result = self.bridge.handle_turn(req)
            # handle_turn returns {"assistant": {"text": "..."}, ...}
            reply = ""
            if isinstance(result, dict):
                assistant = result.get("assistant")
                if isinstance(assistant, dict):
                    reply = assistant.get("text", "")
                if not reply:
                    reply = result.get("reply", result.get("response", ""))
        except Exception as exc:
            reply = f"[Error from {being_id}: {exc}]"
        finally:
            # Restore online + stop typing regardless of success or failure
            self.update_being(being_id, {"status": "online"})
            self._emit_event("being_typing", {
                "being_id": being_id,
                "being_name": being.get("name", being_id),
                "active": False,
            })

        self.create_message(
            sender=being_id,
            content=reply or f"[{being_id} returned empty response]",
            targets=[sender],
            msg_type="direct",
        )

    # ------------------------------------------------------------------
    # Tasks  (wraps ProjectService)
    # ------------------------------------------------------------------

    def ensure_mc_project(self, project_service: Any) -> None:
        """Create the Mission Control project if it does not exist."""
        try:
            project_service.get_project(MC_TENANT, MC_PROJECT_ID)
        except ValueError:
            project_service.create_project(
                tenant_id=MC_TENANT,
                name=MC_PROJECT_NAME,
                workspace_root=str(Path.cwd()),
                project_id=MC_PROJECT_ID,
            )

    def list_tasks(
        self,
        project_service: Any,
        assignee: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        tasks = project_service.list_tasks(MC_TENANT, MC_PROJECT_ID, status=status)
        if priority:
            tasks = [t for t in tasks if t.get("priority") == priority]

        # Enrich with assignees
        for t in tasks:
            rows = self.db.execute(
                "SELECT being_id FROM mc_task_assignments WHERE task_id = ?",
                (t["task_id"],),
            ).fetchall()
            t["assignees"] = [r["being_id"] for r in rows]

        if assignee:
            tasks = [t for t in tasks if assignee in t.get("assignees", [])]
        if from_date:
            tasks = [t for t in tasks if t.get("created_at", "") >= from_date]
        if to_date:
            tasks = [t for t in tasks if t.get("created_at", "") <= to_date]
        return [self._normalize_task(t) for t in tasks]

    def get_task(self, project_service: Any, task_id: str) -> dict:
        task = project_service.get_task(MC_TENANT, task_id)
        rows = self.db.execute(
            "SELECT being_id FROM mc_task_assignments WHERE task_id = ?",
            (task_id,),
        ).fetchall()
        task["assignees"] = [r["being_id"] for r in rows]
        task["history"] = self.task_history(task_id)
        return self._normalize_task(task)

    def create_task(
        self,
        project_service: Any,
        title: str,
        description: str | None = None,
        status: str = "backlog",
        priority: str = "medium",
        assignees: list[str] | None = None,
        owner_agent_id: str | None = None,
    ) -> dict:
        task = project_service.create_task(
            tenant_id=MC_TENANT,
            project_id=MC_PROJECT_ID,
            title=title,
            description=description,
            status=status,
            priority=priority,
            owner_agent_id=owner_agent_id,
        )
        tid = task["task_id"]
        if assignees:
            for bid in assignees:
                self.db.execute(
                    "INSERT OR IGNORE INTO mc_task_assignments (task_id, being_id) VALUES (?,?)",
                    (tid, bid),
                )
            self.db.commit()
            task["assignees"] = assignees
        else:
            task["assignees"] = []

        self._log_task_history(tid, "created", {"title": title, "status": status, "priority": priority})
        self._emit_event("task_update", {"action": "created", "task": self._normalize_task(task)})
        return self._normalize_task(task)

    def update_task(
        self,
        project_service: Any,
        task_id: str,
        status: str | None = None,
        priority: str | None = None,
        owner_agent_id: str | None = None,
        assignees: list[str] | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> dict:
        changes: dict[str, Any] = {}
        if status:
            changes["status"] = status
        if priority:
            changes["priority"] = priority

        # ProjectService.update_task only handles status/priority/owner
        task = project_service.update_task(
            tenant_id=MC_TENANT,
            task_id=task_id,
            status=status,
            priority=priority,
            owner_agent_id=owner_agent_id,
        )

        # title/description need direct SQL
        if title or description:
            sets = []
            params: list[Any] = []
            if title:
                sets.append("title = ?")
                params.append(title)
                changes["title"] = title
            if description:
                sets.append("description = ?")
                params.append(description)
                changes["description"] = description
            sets.append("updated_at = ?")
            params.append(self._now())
            params.append(task_id)
            params.append(MC_TENANT)
            self.db.execute(
                f"UPDATE project_tasks SET {', '.join(sets)} WHERE task_id = ? AND tenant_id = ?",
                params,
            )
            self.db.commit()
            task = project_service.get_task(MC_TENANT, task_id)

        if assignees is not None:
            self.db.execute("DELETE FROM mc_task_assignments WHERE task_id = ?", (task_id,))
            for bid in assignees:
                self.db.execute(
                    "INSERT OR IGNORE INTO mc_task_assignments (task_id, being_id) VALUES (?,?)",
                    (task_id, bid),
                )
            self.db.commit()
            changes["assignees"] = assignees

        rows = self.db.execute(
            "SELECT being_id FROM mc_task_assignments WHERE task_id = ?", (task_id,)
        ).fetchall()
        task["assignees"] = [r["being_id"] for r in rows]

        if changes:
            self._log_task_history(task_id, "updated", changes)
        normalized = self._normalize_task(task)
        self._emit_event("task_update", {"action": "updated", "task": normalized})
        return normalized

    def delete_task(self, project_service: Any, task_id: str) -> bool:
        try:
            project_service.get_task(MC_TENANT, task_id)
        except ValueError:
            return False
        self.db.execute(
            "DELETE FROM project_tasks WHERE tenant_id = ? AND task_id = ?",
            (MC_TENANT, task_id),
        )
        self.db.execute("DELETE FROM mc_task_assignments WHERE task_id = ?", (task_id,))
        self.db.commit()
        self._log_task_history(task_id, "deleted", {})
        self._emit_event("task_update", {"action": "deleted", "task_id": task_id})
        return True

    def task_history(self, task_id: str | None = None, limit: int = 50) -> list[dict]:
        if task_id:
            rows = self.db.execute(
                "SELECT * FROM mc_task_history WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?",
                (task_id, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM mc_task_history ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Parse JSON details so the frontend receives an object, not a string
            if isinstance(d.get("details"), str):
                try:
                    d["details"] = json.loads(d["details"])
                except (json.JSONDecodeError, TypeError):
                    d["details"] = {}
            result.append(d)
        return result

    def _log_task_history(self, task_id: str, action: str, details: dict) -> None:
        self.db.execute(
            "INSERT INTO mc_task_history (id,task_id,action,details,timestamp) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), task_id, action, json.dumps(details), self._now()),
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Sub-agents
    # ------------------------------------------------------------------

    def list_subagent_runs(self) -> list[dict]:
        """Query subagent_runs table if it exists."""
        try:
            rows = self.db.execute(
                """SELECT * FROM subagent_runs
                   ORDER BY created_at DESC LIMIT 50"""
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # SSE
    # ------------------------------------------------------------------

    def subscribe_sse(self) -> str:
        """Create an SSE subscription.  Returns client_id."""
        client_id = str(uuid.uuid4())
        with self._sse_lock:
            self._sse_clients[client_id] = queue.Queue()
        return client_id

    def unsubscribe_sse(self, client_id: str) -> None:
        with self._sse_lock:
            self._sse_clients.pop(client_id, None)

    def poll_sse(self, client_id: str, timeout: float = 20.0) -> dict | None:
        """Block up to *timeout* seconds for the next event."""
        q = self._sse_clients.get(client_id)
        if q is None:
            return None
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def _emit_event(self, event_type: str, payload: dict) -> None:
        now = self._now()
        # Persist
        self.db.execute(
            "INSERT INTO mc_events (event_type, payload, created_at) VALUES (?,?,?)",
            (event_type, json.dumps(payload, default=str), now),
        )
        self.db.commit()

        # Fan-out
        evt = {"event": event_type, "data": payload, "ts": now}
        with self._sse_lock:
            dead: list[str] = []
            for cid, q in self._sse_clients.items():
                try:
                    q.put_nowait(evt)
                except queue.Full:
                    dead.append(cid)
            for cid in dead:
                self._sse_clients.pop(cid, None)

    # ------------------------------------------------------------------
    # Being detail
    # ------------------------------------------------------------------

    # Identity files to look for in a being's workspace
    _IDENTITY_FILES = (
        "SOUL.md", "IDENTITY.md", "MISSION.md", "VISION.md",
        "FORMULA.md", "PRIORITIES.md",
    )

    def get_being_detail(self, being_id: str) -> dict | None:
        """Return enriched detail payload for a single being.

        Scans the being's workspace directory for identity files, memory
        directory, skills, and builds a file tree (2 levels deep).
        """
        being = self.get_being(being_id)
        if not being:
            return None

        ws_rel = being.get("workspace") or ""
        ws_abs = (_PROJECT_ROOT / ws_rel).resolve() if ws_rel else None
        ws_exists = ws_abs is not None and ws_abs.is_dir()

        # ── 1. Identity section ──────────────────────────────────
        identity_files: list[dict] = []
        first_contact: str | None = None
        if ws_exists:
            for fname in self._IDENTITY_FILES:
                fpath = ws_abs / fname
                if fpath.is_file():
                    stat = fpath.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    identity_files.append({
                        "name": fname,
                        "rel_path": str(fpath.relative_to(_PROJECT_ROOT)),
                        "size": stat.st_size,
                        "modified": mtime,
                    })
                    if first_contact is None or mtime < first_contact:
                        first_contact = mtime

            # Also pick up extra workspace-level docs
            for fname in ("AGENTS.md", "TOOLS.md", "SECURITY.md",
                          "HEARTBEAT.md", "USER.md", "BOOTSTRAP.md",
                          "MEMORY.md", "FORGE.md"):
                fpath = ws_abs / fname
                if fpath.is_file():
                    stat = fpath.stat()
                    identity_files.append({
                        "name": fname,
                        "rel_path": str(fpath.relative_to(_PROJECT_ROOT)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })

        soul = self._load_soul_safe(ws_abs) if ws_exists else None

        identity = {
            "name": being["name"],
            "role": being.get("role", ""),
            "status": being.get("status", "offline"),
            "avatar": being.get("avatar", ""),
            "workspace": ws_rel,
            "workspace_abs": str(ws_abs) if ws_abs else None,
            "first_contact": first_contact,
            "model_id": being.get("model_id", ""),
            "tenant_id": being.get("tenant_id", ""),
            "type": being.get("type", ""),
            "color": being.get("color", ""),
            "agent_id": being.get("agent_id", ""),
            "phone": being.get("phone", ""),
            "auto_start": being.get("auto_start", False),
            "description": being.get("description", ""),
            "creature_type": soul.creature_type if soul else None,
            "personality_traits": list(soul.personality_traits) if soul else [],
            "core_functions": list(soul.core_functions) if soul else [],
            "never_do": list(soul.never_do) if soul else [],
            "files": identity_files,
        }

        # ── 2. Memory section ────────────────────────────────────
        memory_info = self._scan_memory(ws_abs, ws_rel) if ws_exists else {
            "path": None, "file_count": 0, "total_size": 0,
            "last_updated": None, "files": [],
        }

        # ── 3. Tools section ─────────────────────────────────────
        tools_list = self._resolve_tools(being, ws_abs if ws_exists else None)

        # ── 4. Skills section ────────────────────────────────────
        skills_list = self._resolve_skills(being, ws_abs if ws_exists else None)

        # ── 5. Workspace file tree ───────────────────────────────
        file_tree = self._build_file_tree(ws_abs, max_depth=2) if ws_exists else []

        return {
            "being": being,
            "identity": identity,
            "memory": memory_info,
            "tools": tools_list,
            "skills": skills_list,
            "file_tree": file_tree,
        }

    def get_being_file(self, being_id: str, rel_path: str) -> str | None:
        """Read a file relative to PROJECT_ROOT and return its text content.

        Security: only files under PROJECT_ROOT are served.
        """
        being = self.get_being(being_id)
        if not being:
            return None

        try:
            target = (_PROJECT_ROOT / rel_path).resolve()
            if not str(target).startswith(str(_PROJECT_ROOT.resolve())):
                return None
        except (ValueError, OSError):
            return None

        if not target.is_file():
            return None

        try:
            return target.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return None

    # ── Detail sub-scanners ──────────────────────────────────────

    @staticmethod
    def _scan_memory(ws_abs: Path, ws_rel: str) -> dict:
        """Scan the memory/ directory under a workspace (recursive)."""
        memory_dir = ws_abs / "memory"
        if not memory_dir.is_dir():
            return {
                "path": None, "file_count": 0, "total_size": 0,
                "last_updated": None, "files": [], "directories": [],
            }

        files: list[dict] = []
        directories: list[str] = []
        total_size = 0
        last_mtime = 0.0

        for entry in sorted(memory_dir.rglob("*")):
            if any(p.startswith(".") for p in entry.relative_to(memory_dir).parts):
                continue
            if entry.is_dir():
                directories.append(str(entry.relative_to(memory_dir)))
                continue
            if entry.is_file():
                stat = entry.stat()
                total_size += stat.st_size
                if stat.st_mtime > last_mtime:
                    last_mtime = stat.st_mtime
                files.append({
                    "name": entry.name,
                    "rel_path": str(entry.relative_to(_PROJECT_ROOT)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                })

        return {
            "path": f"{ws_rel}/memory",
            "file_count": len(files),
            "total_size": total_size,
            "last_updated": (
                datetime.fromtimestamp(last_mtime, tz=timezone.utc).isoformat()
                if last_mtime > 0 else None
            ),
            "files": files,
            "directories": sorted(directories),
        }

    @staticmethod
    def _resolve_tools(being: dict, ws_abs: Path | None) -> list[dict]:
        """Return tool definitions for a being."""
        tools: list[dict] = []
        seen_names: set[str] = set()

        raw_tools = being.get("tools") or []
        for t in raw_tools:
            name = t if isinstance(t, str) else (t.get("name", "") if isinstance(t, dict) else str(t))
            if name and name not in seen_names:
                seen_names.add(name)
                tools.append({
                    "name": name,
                    "description": t.get("description", "") if isinstance(t, dict) else "",
                    "status": "active",
                })

        if not ws_abs:
            return tools

        # Parse TOOLS.md for additional entries
        tools_md = ws_abs / "TOOLS.md"
        if tools_md.is_file():
            try:
                text = tools_md.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("- **") or line_s.startswith("* **"):
                        parts = line_s.split("**")
                        if len(parts) >= 3:
                            tname = parts[1].strip()
                            desc_raw = parts[2].strip()
                            for sep in ("\u2014", "-", ":", "\u2013"):
                                if desc_raw.startswith(sep):
                                    desc_raw = desc_raw[len(sep):].strip()
                            if tname and tname not in seen_names:
                                seen_names.add(tname)
                                tools.append({
                                    "name": tname,
                                    "description": desc_raw[:200],
                                    "status": "available",
                                })
            except OSError:
                pass

        # Workspace tools/ directory scripts
        tools_dir = ws_abs / "tools"
        if tools_dir.is_dir():
            for entry in sorted(tools_dir.iterdir()):
                if entry.is_file() and not entry.name.startswith("."):
                    tname = entry.stem
                    if tname not in seen_names:
                        seen_names.add(tname)
                        tools.append({
                            "name": tname,
                            "description": f"Tool script: {entry.name}",
                            "status": "available",
                        })

        return tools

    @staticmethod
    def _resolve_skills(being: dict, ws_abs: Path | None) -> list[dict]:
        """Return skill definitions for a being."""
        skills: list[dict] = []
        seen_names: set[str] = set()

        raw_skills = being.get("skills") or []
        for s in raw_skills:
            name = s if isinstance(s, str) else str(s)
            if name and name not in seen_names:
                seen_names.add(name)
                skills.append({"name": name, "description": "", "path": None})

        # Global skills/ directory
        global_skills_dir = _PROJECT_ROOT / "skills"
        if global_skills_dir.is_dir():
            for entry in sorted(global_skills_dir.iterdir()):
                if entry.is_dir():
                    skill_md = entry / "SKILL.md"
                    sname = entry.name
                    if sname not in seen_names:
                        seen_names.add(sname)
                        desc = ""
                        if skill_md.is_file():
                            try:
                                text = skill_md.read_text(encoding="utf-8", errors="replace")
                                in_fm = False
                                for sline in text.splitlines():
                                    stripped = sline.strip()
                                    if stripped == "---":
                                        in_fm = not in_fm
                                        continue
                                    if not in_fm and stripped and not stripped.startswith("#"):
                                        desc = stripped[:200]
                                        break
                            except OSError:
                                pass
                        skills.append({
                            "name": sname,
                            "description": desc,
                            "path": str(entry.relative_to(_PROJECT_ROOT)),
                        })

        return skills

    @staticmethod
    def _build_file_tree(ws_abs: Path, max_depth: int = 2) -> list[dict]:
        """Build a file/directory tree for the workspace (limited depth)."""

        def _scan(directory: Path, depth: int) -> list[dict]:
            if depth > max_depth:
                return []
            entries: list[dict] = []
            try:
                items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            except OSError:
                return []
            for item in items:
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    children = _scan(item, depth + 1) if depth < max_depth else []
                    entries.append({
                        "name": item.name,
                        "type": "dir",
                        "rel_path": str(item.relative_to(_PROJECT_ROOT)),
                        "children": children,
                    })
                elif item.is_file():
                    entries.append({
                        "name": item.name,
                        "type": "file",
                        "rel_path": str(item.relative_to(_PROJECT_ROOT)),
                        "size": item.stat().st_size,
                    })
            return entries

        return _scan(ws_abs, 0)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_soul_safe(workspace_path: Path):
        """Load SoulConfig from a workspace, returning None on any error."""
        try:
            from bomba_sr.identity.soul import load_soul_from_workspace
            return load_soul_from_workspace(workspace_path)
        except Exception:
            return None

    @staticmethod
    def _color_for_sister(sister_id: str) -> str:
        """Assign a consistent color to each known sister."""
        colors = {
            "forge": "#EF4444",     # red
            "scholar": "#3B82F6",   # blue
            "recovery": "#10B981",  # green
        }
        return colors.get(sister_id, "#6B7280")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _being_row(row) -> dict:
        d = dict(row)
        for field in ("tools", "skills", "metrics"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        d["auto_start"] = bool(d.get("auto_start"))
        return d

    @staticmethod
    def _message_row(row) -> dict:
        d = dict(row)
        if "targets" in d and isinstance(d["targets"], str):
            try:
                d["targets"] = json.loads(d["targets"])
            except (json.JSONDecodeError, TypeError):
                d["targets"] = []
        return d

    @staticmethod
    def _normalize_task(task: dict) -> dict:
        """Map ProjectService field names to the shape the frontend expects.

        Backend returns: task_id, created_at, updated_at
        Frontend expects: id, created, updated
        """
        t = dict(task)
        # Rename task_id -> id (keep task_id for backwards compat)
        if "task_id" in t and "id" not in t:
            t["id"] = t["task_id"]
        # Rename created_at -> created
        if "created_at" in t and "created" not in t:
            t["created"] = t["created_at"]
        # Rename updated_at -> updated
        if "updated_at" in t and "updated" not in t:
            t["updated"] = t["updated_at"]
        # Ensure assignees always present as a list
        if "assignees" not in t:
            t["assignees"] = []
        return t

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
