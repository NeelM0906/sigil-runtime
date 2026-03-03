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
            "name": prime_soul.name if prime_soul else "Prime",
            "role": "Lead orchestrator — holds the vision, coordinates all sisters",
            "avatar": prime_soul.emoji if prime_soul else "🔥",
            "status": "online",
            "description": "The host runtime. Coordinates all sisters and sub-agents.",
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

        # ── Tier 3: .sai-analysis sisters ─────────────────────────
        sai_sisters_dir = _PROJECT_ROOT / ".sai-analysis" / "sisters"
        if sai_sisters_dir.is_dir():
            tier3_configs = {
                "sai-memory": {
                    "id": "memory",
                    "tenant_id": "tenant-memory",
                    "color": "#8B5CF6",
                    "type": TYPE_SISTER,
                },
                "sai-recovery": {
                    "id": "sai-recovery",
                    "tenant_id": "tenant-recovery",
                    "color": "#10B981",
                    "type": TYPE_SISTER,
                },
            }
            for dirname, cfg in tier3_configs.items():
                sister_dir = sai_sisters_dir / dirname
                if not sister_dir.is_dir():
                    continue
                soul = self._load_soul_safe(sister_dir)
                beings.append({
                    "id": cfg["id"],
                    "name": soul.name if soul else dirname.replace("sai-", "SAI ").title(),
                    "role": (soul.raw_soul_text or "")[:200].split("\n")[0] if soul else "",
                    "avatar": soul.emoji if soul else "",
                    "status": "online",
                    "description": f"Tier 3 sister from .sai-analysis/{dirname}",
                    "type": cfg["type"],
                    "tools": [],
                    "skills": [],
                    "color": cfg["color"],
                    "model_id": "",
                    "workspace": f".sai-analysis/sisters/{dirname}",
                    "tenant_id": cfg["tenant_id"],
                    "auto_start": False,
                })

            # Tier 3 sub-agents: BD-PIP and BD-WC under sai-recovery/agents/
            bd_agents_dir = sai_sisters_dir / "sai-recovery" / "agents"
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
                    identity_path = agent_dir / "IDENTITY.md"
                    if not identity_path.exists():
                        continue
                    soul = self._load_soul_safe(agent_dir)
                    beings.append({
                        "id": cfg["id"],
                        "name": soul.name if soul else dirname.upper(),
                        "role": cfg["role"],
                        "avatar": soul.emoji if soul else "🎯",
                        "status": "online",
                        "description": cfg["role"],
                        "type": TYPE_SUBAGENT,
                        "tools": [],
                        "skills": [],
                        "color": cfg["color"],
                        "model_id": "",
                        "workspace": f".sai-analysis/sisters/sai-recovery/agents/{dirname}",
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
        return tasks

    def get_task(self, project_service: Any, task_id: str) -> dict:
        task = project_service.get_task(MC_TENANT, task_id)
        rows = self.db.execute(
            "SELECT being_id FROM mc_task_assignments WHERE task_id = ?",
            (task_id,),
        ).fetchall()
        task["assignees"] = [r["being_id"] for r in rows]
        task["history"] = self.task_history(task_id)
        return task

    def create_task(
        self,
        project_service: Any,
        title: str,
        description: str | None = None,
        status: str = "todo",
        priority: str = "normal",
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
        self._emit_event("task_update", {"action": "created", "task": task})
        return task

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
        self._emit_event("task_update", {"action": "updated", "task": task})
        return task

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
        return [dict(r) for r in rows]

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
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
