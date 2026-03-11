"""Mission Control dashboard service.

Owns mc_* tables for beings registry, chat messages, task history,
and SSE event streaming.  Delegates to ProjectService for task CRUD
and RuntimeBridge for real LLM routing.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.storage.db import RuntimeDB, dict_from_row
from bomba_sr.acti.loader import (
    get_full_architecture,
    get_sister_profile,
    SHARED_HEART_SKILLS,
    BEING_SISTER_MAP,
)


MC_TENANT = "tenant-local"
MC_PROJECT_ID = "mc-project"
MC_PROJECT_NAME = "Mission Control"

# Being types
TYPE_SISTER = "sister"
TYPE_RUNTIME = "runtime"       # Prime — the host runtime itself
TYPE_VOICE_AGENT = "voice"     # Bland.ai voice agents — not chat-routable
TYPE_SUBAGENT = "subagent"     # BD-PIP, BD-WC etc.
TYPE_ACTI = "acti"             # ACT-I specialized beings

log = logging.getLogger(__name__)

# ── Task classification ──────────────────────────────────────
# Fast model for classification calls (cheap, low-latency).
_CLASSIFY_MODEL = os.getenv("BOMBA_CLASSIFY_MODEL", "openai/gpt-4o-mini")

_CLASSIFY_SYSTEM_PROMPT = """\
You are a message classifier for a multi-agent command center.
Given a user message sent to an AI being, classify it into exactly one category:

- "not_task" — casual/conversational, greetings, questions about the being itself, \
information requests with no concrete action required. Examples: "Hi", "How are you?", \
"What's in your memory?", "Tell me about yourself."
- "light_task" — needs a single action or lookup, no multi-step plan needed. \
Examples: "Search Pinecone for X", "Summarize this document", "What's the status of Y."
- "full_task" — needs multi-step execution that benefits from a tracked plan with sub-steps. \
Examples: "Research X and write a report", "Audit all memory files and flag inconsistencies", \
"Set up the integration for Recovery."

Respond with ONLY a JSON object: {"classification": "not_task"|"light_task"|"full_task"}
Nothing else."""

_CLASSIFY_PROMPT_TEMPLATE = 'Message: "{message}"\nClassification:'

# Pattern-based fast-path for obvious non-tasks (avoids LLM call).
_NOT_TASK_PATTERNS = re.compile(
    r"^("
    r"h(i|ey|ello|owdy|ola)"
    r"|yo\b"
    r"|what'?s up"
    r"|good (morning|afternoon|evening|night)"
    r"|thanks?"
    r"|thank you"
    r"|ok(ay)?"
    r"|sure"
    r"|bye"
    r"|see ya"
    r"|how are you"
    r"|how'?s it going"
    r"|tell me about yourself"
    r"|who are you"
    r"|what are you"
    r"|what can you do"
    r"|what tools do you have"
    r"|what tools are available"
    r"|show me your tools"
    r"|list your tools"
    r"|what do you know"
    r"|what are your capabilities"
    r"|gm"
    r"|gn"
    r"|sup"
    r")"
    r"(\s+\S+){0,4}"   # Allow up to 4 trailing words (e.g. "hey how are you doing")
    r"[\s?!.,]*$",
    re.IGNORECASE,
)

_REPRESENTATION_KEYWORDS = re.compile(
    r"\b(capabilities?|history|performance|strengths?|weaknesses?"
    r"|track\s+record|how.*been\s+doing|past\s+tasks?|profile|background)\b",
    re.IGNORECASE,
)

_STEP_GENERATION_PROMPT = """\
You are planning sub-steps for an AI agent task.
Given the task message, break it into 2-6 concrete sub-steps the agent should follow.
Each step should be a short imperative sentence (max 60 chars).

Respond with ONLY a JSON object: {"steps": ["step 1", "step 2", ...]}
Nothing else."""

# ── Being → Skill mapping ────────────────────────────────────
# Default skills each being has access to. Any being can request
# a skill it doesn't have by default if the task requires it.

BEING_SKILL_MAP: dict[str, list[str]] = {
    # All beings get these by default
    "__default__": ["pdf-generator", "docx-generator", "code-generator"],
    # Per-being additions
    "sai-forge": ["screenshot"],
    "sai-scholar": ["screenshot"],
    "sai-recovery": [],
    "sai-memory": [],
}


def get_being_skills(being_id: str) -> list[str]:
    """Return the skill IDs available to a being."""
    defaults = list(BEING_SKILL_MAP.get("__default__", []))
    extras = BEING_SKILL_MAP.get(being_id, [])
    # Add shared heart skills from ACT-I
    heart = [s["id"] for s in SHARED_HEART_SKILLS]
    return defaults + extras + heart


def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from an LLM response (tolerates markdown fences)."""
    stripped = text.strip()
    if not stripped:
        return None
    candidates: list[str] = [stripped]
    fenced = re.findall(
        r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE
    )
    candidates.extend(fenced)
    brace = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None

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
        self.project_service: Any | None = None
        self.orchestration_engine: Any | None = None
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

            CREATE TABLE IF NOT EXISTS mc_task_steps (
              id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              step_number INTEGER NOT NULL,
              label TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              updated_at TEXT NOT NULL,
              UNIQUE(task_id, step_number)
            );
            CREATE INDEX IF NOT EXISTS idx_mc_task_steps_task
              ON mc_task_steps(task_id, step_number);

            CREATE TABLE IF NOT EXISTS mc_events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mc_events_type
              ON mc_events(event_type, seq);

            CREATE TABLE IF NOT EXISTS mc_chat_sessions (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mc_deliverables (
              id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              being_id TEXT,
              filename TEXT NOT NULL,
              file_type TEXT NOT NULL,
              file_path TEXT NOT NULL,
              url TEXT NOT NULL,
              line_count INTEGER DEFAULT 0,
              byte_size INTEGER DEFAULT 0,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mc_deliverables_task
              ON mc_deliverables(task_id);
        """)
        self.db.commit()

        # Migration: add session_id to mc_messages
        try:
            self.db.execute("ALTER TABLE mc_messages ADD COLUMN session_id TEXT DEFAULT 'general'")
            self.db.commit()
        except Exception:
            pass  # column already exists
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_mc_messages_session ON mc_messages(session_id, timestamp DESC)")
        self.db.execute("UPDATE mc_messages SET session_id = 'general' WHERE session_id IS NULL")
        # Seed default General session
        now = self._now()
        self.db.execute_commit(
            "INSERT OR IGNORE INTO mc_chat_sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("general", "General", now, now),
        )

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
        data = json.loads(path.read_text(encoding="utf-8"))
        beings = data.get("beings", data) if isinstance(data, dict) else data

        now = self._now()
        inserted = 0
        with self.db.transaction() as conn:
            for b in beings:
                self._upsert_being_conn(conn, b, now)
                inserted += 1
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
                data = json.loads(sisters_json.read_text(encoding="utf-8"))
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
                    bland_data = json.loads(config_path.read_text(encoding="utf-8"))
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

        # ── Tier 3: ACT-I specialized beings ──────────────────────
        try:
            from bomba_sr.acti.loader import load_beings as load_acti_beings, SHARED_HEART_SKILLS as _ACTI_HEART

            # Build a lookup for sister tenant_id/workspace/color/model from already-loaded beings
            sister_lookup: dict[str, dict] = {}
            for b in beings:
                if b.get("type") == TYPE_SISTER:
                    sister_lookup[b["id"]] = b

            acti_beings = load_acti_beings()
            for ab in acti_beings:
                # Skip apex beings (Prime, Executive Assistant) — they're already loaded
                if ab["id"] in ("sai-prime", "executive-assistant"):
                    continue
                sister_id = ab.get("sister_id", "")
                parent = sister_lookup.get(sister_id, {})
                top_clusters = ab.get("clusters", [])[:3]
                beings.append({
                    "id": ab["id"],
                    "name": ab["name"],
                    "role": (ab.get("domain") or "")[:200],
                    "avatar": "\U0001f3af",  # 🎯
                    "status": "online",
                    "description": ab.get("domain", ""),
                    "type": TYPE_ACTI,
                    "tools": [],
                    "skills": [s["name"] for s in _ACTI_HEART] + [c["name"] for c in top_clusters],
                    "color": parent.get("color", self._color_for_sister(sister_id)),
                    "model_id": parent.get("model_id", ""),
                    "workspace": parent.get("workspace", f"workspaces/{sister_id}"),
                    "tenant_id": parent.get("tenant_id", f"tenant-{sister_id}"),
                    "auto_start": False,
                })
        except Exception:
            pass  # ACT-I data not available — skip silently

        # ── Upsert all beings ─────────────────────────────────────
        now = self._now()
        with self.db.transaction() as conn:
            for b in beings:
                self._upsert_being_conn(conn, b, now)
        return len(beings)

    def _upsert_being(self, b: dict, now: str) -> None:
        """Insert or update a being record (standalone, auto-commits)."""
        with self.db.transaction() as conn:
            self._upsert_being_conn(conn, b, now)

    def _upsert_being_conn(self, conn: Any, b: dict, now: str) -> None:
        """Insert or update a being record using the given connection."""
        existing = conn.execute(
            "SELECT id FROM mc_beings WHERE id = ?", (b["id"],)
        ).fetchone()
        if existing:
            conn.execute(
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
            conn.execute(
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
        beings = [self._being_row(r) for r in rows]
        # Enrich with active task info for detailed status
        for b in beings:
            b["active_task"] = self._get_being_active_task(b["id"])
            b["status_detail"] = self._compute_status_detail(b)
        return beings

    def _get_being_active_task(self, being_id: str) -> dict | None:
        """Find the active in_progress task assigned to this being."""
        try:
            row = self.db.execute(
                """SELECT pt.task_id, pt.title, pt.status
                   FROM mc_task_assignments ma
                   JOIN project_tasks pt ON pt.task_id = ma.task_id
                   WHERE ma.being_id = ? AND pt.status = 'in_progress'
                   ORDER BY pt.updated_at DESC LIMIT 1""",
                (being_id,),
            ).fetchone()
            if row is None:
                return None
            return {"task_id": str(row["task_id"]), "title": str(row["title"]), "status": str(row["status"])}
        except Exception:
            return None

    def _compute_status_detail(self, being: dict) -> str:
        """Compute detailed status string for display.

        Returns one of:
          - "online" — available, no active tasks
          - "busy (chat)" — responding to user in chat
          - "busy (task: {name})" — working a delegated sub-task
          - "orchestrating ({name})" — Prime only, coordinating multi-being task
          - "offline" — not available
        """
        base_status = being.get("status", "offline")
        if base_status == "offline":
            return "offline"

        active_task = being.get("active_task")
        being_id = being.get("id", "")

        # Check if Prime is orchestrating
        if being_id == "prime" and self.orchestration_engine is not None:
            for state in (self.orchestration_engine._active or {}).values():
                if state.get("status") not in ("completed", "failed"):
                    task_name = state.get("goal", "")[:40]
                    return f"orchestrating ({task_name})"

        if base_status == "busy":
            if active_task:
                task_name = active_task.get("title", "")[:40]
                return f"busy (task: {task_name})"
            return "busy (chat)"

        if active_task:
            task_name = active_task.get("title", "")[:40]
            return f"busy (task: {task_name})"

        return "online"

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

        self.db.execute_commit(
            f"UPDATE mc_beings SET {', '.join(sets)} WHERE id = ?", params
        )

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
        with self.db.transaction() as conn:
            for s in sisters:
                sid = s.get("sister_id") or s.get("id")
                status = "online" if s.get("running") else "offline"
                conn.execute(
                    "UPDATE mc_beings SET status = ?, updated_at = ? WHERE id = ?",
                    (status, self._now(), sid),
                )

    # ------------------------------------------------------------------
    # Chat sessions
    # ------------------------------------------------------------------

    def list_sessions(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM mc_chat_sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def create_session(self, name: str) -> dict:
        sid = f"sess-{uuid.uuid4().hex[:8]}"
        now = self._now()
        self.db.execute_commit(
            "INSERT INTO mc_chat_sessions (id, name, created_at, updated_at) VALUES (?,?,?,?)",
            (sid, name, now, now),
        )
        session = dict(self.db.execute(
            "SELECT * FROM mc_chat_sessions WHERE id = ?", (sid,)
        ).fetchone())
        self._emit_event("chat_session", {"action": "created", "session": session})
        return session

    def rename_session(self, session_id: str, name: str) -> dict:
        now = self._now()
        self.db.execute_commit(
            "UPDATE mc_chat_sessions SET name = ?, updated_at = ? WHERE id = ?",
            (name, now, session_id),
        )
        session = dict(self.db.execute(
            "SELECT * FROM mc_chat_sessions WHERE id = ?", (session_id,)
        ).fetchone())
        self._emit_event("chat_session", {"action": "updated", "session": session})
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id == "general":
            return False
        self.db.execute_commit("DELETE FROM mc_messages WHERE session_id = ?", (session_id,))
        cur = self.db.execute_commit("DELETE FROM mc_chat_sessions WHERE id = ?", (session_id,))
        if cur.rowcount > 0:
            self._emit_event("chat_session", {"action": "deleted", "session_id": session_id})
            return True
        return False

    # ------------------------------------------------------------------
    # Deliverables
    # ------------------------------------------------------------------

    def create_deliverable(
        self,
        task_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        url: str,
        being_id: str | None = None,
        line_count: int = 0,
        byte_size: int = 0,
    ) -> dict:
        did = f"dlv-{uuid.uuid4().hex[:8]}"
        now = self._now()
        self.db.execute_commit(
            """INSERT INTO mc_deliverables
               (id, task_id, being_id, filename, file_type, file_path, url, line_count, byte_size, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (did, task_id, being_id, filename, file_type, file_path, url, line_count, byte_size, now),
        )
        row = self.db.execute("SELECT * FROM mc_deliverables WHERE id = ?", (did,)).fetchone()
        d = dict(row)
        self._emit_event("deliverable_created", d)
        return d

    def list_deliverables(self, task_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM mc_deliverables WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all_deliverables(self, limit: int = 50) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM mc_deliverables ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Chat messages
    # ------------------------------------------------------------------

    def list_messages(
        self,
        sender: str | None = None,
        target: str | None = None,
        search: str | None = None,
        session_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        sql = "SELECT * FROM mc_messages WHERE 1=1"
        params: list[Any] = []
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
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
        session_id: str = "general",
    ) -> dict:
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        now = self._now()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO mc_messages
                   (id,type,sender,targets,content,timestamp,mode,task_ref,session_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    msg_id, msg_type, sender,
                    json.dumps(targets or []),
                    content, now, mode, task_ref, session_id,
                ),
            )
            # Update session timestamp
            conn.execute(
                "UPDATE mc_chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
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
        cur = self.db.execute_commit(
            "DELETE FROM mc_messages WHERE id = ?", (msg_id,)
        )
        return cur.rowcount > 0

    def route_to_being(self, being_id: str, content: str, sender: str = "user", chat_session_id: str = "general") -> None:
        """Route a message to a being via LLM in a background thread."""
        t = threading.Thread(
            target=self._route_to_being_sync,
            args=(being_id, content, sender, chat_session_id),
            daemon=True,
        )
        t.start()

    def _route_to_being_sync(self, being_id: str, content: str, sender: str, chat_session_id: str = "general") -> None:
        """Call bridge.handle_turn for a being and store the response.

        Identity is loaded automatically by the bridge via SoulConfig from
        the being's workspace_root -- no identity prefix hack needed.

        Task board integration:
          - not_task  → no task created (greetings, casual chat)
          - light_task → task auto-created, transitions in_progress → done
          - full_task  → task + sub-steps created, steps advance as being works
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
                session_id=chat_session_id,
            )
            return

        # Offline beings cannot respond
        if being.get("status") == "offline":
            self.create_message(
                sender=being_id,
                content=f"[{being.get('name', being_id)} is currently offline and cannot respond.]",
                targets=[sender],
                msg_type="direct",
                session_id=chat_session_id,
            )
            return

        if not self.bridge:
            self.create_message(
                sender=being_id,
                content=f"[{being_id} is offline — no LLM bridge available]",
                targets=[sender],
                msg_type="direct",
                session_id=chat_session_id,
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

        # ── Classify the message before creating any task ──
        classification = self._classify_message(content)
        log.info(
            '[CLASSIFY] message="%.50s" → %s',
            content.replace('"', "'"),
            classification,
        )

        # ── Orchestration intercept: full_task to Prime triggers multi-being orchestration ──
        if (
            classification == "full_task"
            and being_id == "prime"
            and self.orchestration_engine is not None
            and self.project_service is not None
        ):
            self._handle_orchestrated_task(being_id, being, content, sender, session_id, chat_session_id=chat_session_id)
            return

        task_id: str | None = None
        if classification in ("light_task", "full_task"):
            task_id = self._auto_create_task(being_id, being, content, classification=classification)

        # For full_task, generate and attach sub-steps
        if classification == "full_task" and task_id:
            step_labels = self._generate_task_steps(content)
            if step_labels:
                steps = self.create_task_steps(task_id, step_labels)
                # Mark the first step as in_progress
                if steps:
                    self.update_task_step(steps[0]["id"], "in_progress")

        # Signal busy + typing before calling bridge
        self.update_being(being_id, {"status": "busy"})
        self._emit_event("being_typing", {
            "being_id": being_id,
            "being_name": being.get("name", being_id),
            "active": True,
        })

        # Transition task to in_progress
        if task_id:
            self._auto_update_task_status(task_id, "in_progress")

        # Build step-advancing callback for real-time progress
        all_steps = self.get_task_steps(task_id) if task_id and classification == "full_task" else []
        step_cursor = [0]
        num_steps = len(all_steps)

        def _on_loop_iteration(iteration, loop_state):
            if num_steps == 0 or step_cursor[0] >= num_steps - 1:
                return
            self.advance_task_step(task_id)
            step_cursor[0] += 1

        error_occurred = False
        try:
            from bomba_sr.runtime.bridge import TurnRequest
            _inc_rep = bool(_REPRESENTATION_KEYWORDS.search(content))
            req = TurnRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=sender,
                user_message=content,
                workspace_root=workspace,
                task_id=task_id,
                project_id=MC_PROJECT_ID,
                on_iteration=_on_loop_iteration if all_steps else None,
                include_representation=_inc_rep,
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
            error_occurred = True
        finally:
            # Restore online + stop typing regardless of success or failure
            self.update_being(being_id, {"status": "online"})
            self._emit_event("being_typing", {
                "being_id": being_id,
                "being_name": being.get("name", being_id),
                "active": False,
            })

        # Transition task to done (or back to backlog on error)
        if task_id:
            if error_occurred:
                self._auto_update_task_status(task_id, "backlog")
            else:
                # For full_task, complete all remaining steps
                if classification == "full_task":
                    for step in self.get_task_steps(task_id):
                        if step["status"] != "done":
                            self.update_task_step(step["id"], "done")
                self._auto_update_task_status(task_id, "done")

        self.create_message(
            sender=being_id,
            content=reply or f"[{being_id} returned empty response]",
            targets=[sender],
            msg_type="direct",
            task_ref=task_id,
            session_id=chat_session_id,
        )

    def init_orchestration(self, project_svc: Any) -> None:
        """Initialize the orchestration engine. Call after bridge + project_svc are set."""
        if self.bridge is None:
            return
        from bomba_sr.orchestration.engine import OrchestrationEngine
        self.orchestration_engine = OrchestrationEngine(
            bridge=self.bridge,
            dashboard_svc=self,
            project_svc=project_svc,
        )
        # Clean up stale/orphaned tasks from previous sessions on startup.
        try:
            cleaned = self.cleanup_orphaned_tasks(project_svc)
            if cleaned:
                log.info("Cleaned up %d orphaned tasks on startup", cleaned)
        except Exception as exc:
            log.debug("Orphaned task cleanup failed (non-fatal): %s", exc)
        log.info("Orchestration engine initialized")

    def _handle_orchestrated_task(
        self,
        being_id: str,
        being: dict,
        content: str,
        sender: str,
        session_id: str,
        chat_session_id: str = "general",
    ) -> None:
        """Route a full_task to Prime's orchestration engine instead of direct LLM."""
        # Acknowledge in chat immediately
        self.create_message(
            sender="prime",
            content=(
                f"I'll orchestrate this across the team. "
                f"Planning sub-tasks now — you can track progress on the task board."
            ),
            targets=[sender],
            msg_type="direct",
            session_id=chat_session_id,
        )

        # Update Prime status
        self.update_being("prime", {"status": "busy"})
        self._emit_event("being_status", {
            "being_id": "prime",
            "status": "orchestrating",
            "task_preview": content[:80],
        })

        try:
            result = self.orchestration_engine.start(
                goal=content,
                requester_session_id=session_id,
                sender=sender,
                chat_session_id=chat_session_id,
            )
            log.info(
                "Orchestration started: task=%s status=%s",
                result.get("task_id", "?")[:8],
                result.get("status"),
            )
        except Exception as exc:
            log.exception("Failed to start orchestration")
            self.create_message(
                sender="prime",
                content=f"[Orchestration failed to start: {exc}]",
                targets=[sender],
                msg_type="direct",
                session_id=chat_session_id,
            )
            self.update_being("prime", {"status": "online"})

    def get_orchestration_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the current orchestration status for a task."""
        if self.orchestration_engine is None:
            return None
        return self.orchestration_engine.get_status(task_id)

    def get_orchestration_log(self, task_id: str) -> list[dict[str, Any]]:
        """Get the orchestration log (conversation turns) for a task."""
        if self.orchestration_engine is None:
            return []
        return self.orchestration_engine.get_orchestration_log(task_id)

    # Valid classifications that permit task creation.
    _TASK_CLASSIFICATIONS = frozenset({"light_task", "full_task"})

    def _auto_create_task(
        self,
        being_id: str,
        being: dict,
        content: str,
        *,
        classification: str,
    ) -> str | None:
        """Auto-create a task on the board when a being receives a classified message.

        The ``classification`` parameter is **required** and must be one of
        ``light_task`` or ``full_task``.  Passing ``not_task`` (or any other
        value) raises ``ValueError`` — this is an architectural gate that makes
        it structurally impossible to create a task without a valid classification.
        """
        if classification not in self._TASK_CLASSIFICATIONS:
            raise ValueError(
                f"Cannot create task: classification '{classification}' is not "
                f"a task-creating classification. Must be one of {sorted(self._TASK_CLASSIFICATIONS)}."
            )
        if not self.project_service:
            return None
        try:
            # Truncate content for the title (first line, max 80 chars)
            first_line = content.strip().split("\n")[0]
            title = first_line[:80] + ("..." if len(first_line) > 80 else "")
            being_name = being.get("name", being_id)

            task = self.create_task(
                project_service=self.project_service,
                title=title,
                description=f"Auto-created from chat message to {being_name}",
                status="backlog",
                priority="medium",
                assignees=[being_id],
                owner_agent_id=being_id,
            )
            log.info('[CLASSIFY] Task created: id=%s classification=%s', task.get("id", "?")[:8], classification)
            return task.get("id")
        except Exception:
            return None

    def _auto_update_task_status(self, task_id: str, new_status: str) -> None:
        """Update task status and emit events for real-time board updates."""
        if not self.project_service:
            return
        try:
            self.update_task(
                project_service=self.project_service,
                task_id=task_id,
                status=new_status,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Task classification
    # ------------------------------------------------------------------

    def _classify_message(self, content: str) -> str:
        """Classify a message as not_task, light_task, or full_task.

        Uses a regex fast-path for obvious non-tasks, then falls back to
        a lightweight LLM call for ambiguous messages.
        """
        stripped = content.strip()

        # Fast-path: very short or matches greeting/casual patterns
        if len(stripped) < 4 or _NOT_TASK_PATTERNS.match(stripped):
            return "not_task"

        # LLM classification
        try:
            from bomba_sr.llm.providers import ChatMessage, provider_from_env
            provider = provider_from_env()
            resp = provider.generate(
                model=_CLASSIFY_MODEL,
                messages=[
                    ChatMessage(role="system", content=_CLASSIFY_SYSTEM_PROMPT),
                    ChatMessage(
                        role="user",
                        content=_CLASSIFY_PROMPT_TEMPLATE.format(message=stripped[:500]),
                    ),
                ],
            )
            payload = _extract_json(resp.text)
            if payload:
                classification = payload.get("classification", "not_task")
                if classification in ("not_task", "light_task", "full_task"):
                    return classification
        except Exception as exc:
            log.debug("Task classification failed, defaulting to not_task: %s", exc)

        # Safe default: do NOT create a task when the classifier is uncertain.
        # Creating spurious tasks is worse than missing a real one.
        return "not_task"

    def _generate_task_steps(self, content: str) -> list[str]:
        """Use LLM to break a full_task message into sub-steps."""
        try:
            from bomba_sr.llm.providers import ChatMessage, provider_from_env
            provider = provider_from_env()
            resp = provider.generate(
                model=_CLASSIFY_MODEL,
                messages=[
                    ChatMessage(role="system", content=_STEP_GENERATION_PROMPT),
                    ChatMessage(role="user", content=f'Task: "{content[:500]}"'),
                ],
            )
            payload = _extract_json(resp.text)
            if payload and isinstance(payload.get("steps"), list):
                steps = [str(s)[:60] for s in payload["steps"] if s]
                if steps:
                    return steps[:6]
        except Exception as exc:
            log.debug("Step generation failed: %s", exc)
        return []

    # ------------------------------------------------------------------
    # Task steps CRUD
    # ------------------------------------------------------------------

    def create_task_steps(self, task_id: str, labels: list[str]) -> list[dict]:
        """Create sub-steps for a task. Returns the created step dicts."""
        now = self._now()
        steps = []
        with self.db.transaction() as conn:
            for i, label in enumerate(labels):
                step_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO mc_task_steps (id, task_id, step_number, label, status, updated_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (step_id, task_id, i, label, "pending", now),
                )
                steps.append({
                    "id": step_id,
                    "task_id": task_id,
                    "step_number": i,
                    "label": label,
                    "status": "pending",
                    "updated_at": now,
                })
        self._emit_event("task_steps_update", {"task_id": task_id, "steps": steps})
        return steps

    def update_task_step(self, step_id: str, status: str) -> dict | None:
        """Update a single step's status. Returns updated step or None."""
        now = self._now()
        self.db.execute_commit(
            "UPDATE mc_task_steps SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, step_id),
        )
        row = self.db.execute(
            "SELECT * FROM mc_task_steps WHERE id = ?", (step_id,)
        ).fetchone()
        if not row:
            return None
        step = dict(row)
        self._emit_event("task_steps_update", {
            "task_id": step["task_id"],
            "step": step,
        })
        return step

    def get_task_steps(self, task_id: str) -> list[dict]:
        """Return all steps for a task, ordered by step_number."""
        rows = self.db.execute(
            "SELECT * FROM mc_task_steps WHERE task_id = ? ORDER BY step_number",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def advance_task_step(self, task_id: str) -> dict | None:
        """Mark the first pending step as done and the next as in_progress.

        Returns the step that was just completed, or None.
        """
        steps = self.get_task_steps(task_id)
        completed_step = None
        for step in steps:
            if step["status"] == "in_progress":
                self.update_task_step(step["id"], "done")
                completed_step = step
            elif step["status"] == "pending" and completed_step:
                self.update_task_step(step["id"], "in_progress")
                break
        return completed_step

    # ------------------------------------------------------------------
    # Artifacts (wraps ArtifactStore for dashboard context)
    # ------------------------------------------------------------------

    def set_artifact_store(self, store: Any) -> None:
        """Set the artifact store reference for dashboard artifact tracking."""
        self._artifact_store = store

    def list_task_artifacts(self, task_id: str) -> list[dict]:
        """List artifacts attached to a task."""
        store = getattr(self, "_artifact_store", None)
        if not store:
            return []
        try:
            records = store.list_task_artifacts(MC_TENANT, task_id)
            return [r.to_dict() for r in records]
        except Exception:
            return []

    def get_artifact(self, artifact_id: str) -> dict | None:
        """Get a single artifact record."""
        store = getattr(self, "_artifact_store", None)
        if not store:
            return None
        try:
            rec = store.get_artifact(artifact_id)
            return rec.to_dict() if rec else None
        except Exception:
            return None

    def notify_artifact_created(self, record) -> None:
        """SSE notification when an artifact is created during task execution."""
        d = record.to_dict() if hasattr(record, "to_dict") else record
        task_id = d.get("task_id")
        if task_id:
            self._emit_event("artifact_created", {"task_id": task_id, "artifact": d})

    def get_being_skill_list(self, being_id: str) -> list[dict]:
        """Return skills available to a being with metadata."""
        skill_ids = get_being_skills(being_id)
        skills: list[dict] = []
        for sid in skill_ids:
            # Try to find the SKILL.md for richer metadata
            skill_dir = _PROJECT_ROOT / "skills" / sid.replace("-", "_")
            if not skill_dir.is_dir():
                skill_dir = _PROJECT_ROOT / "skills" / sid
            desc = ""
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.is_file():
                    try:
                        text = skill_md.read_text(encoding="utf-8", errors="replace")
                        # Extract description from YAML frontmatter
                        in_fm = False
                        for line in text.splitlines():
                            s = line.strip()
                            if s == "---":
                                in_fm = not in_fm
                                continue
                            if in_fm and s.startswith("description:"):
                                desc = s.split(":", 1)[1].strip().strip('"\'')
                                break
                    except OSError:
                        pass
            skills.append({"skill_id": sid, "description": desc})
        return skills

    # ------------------------------------------------------------------
    # Tasks  (wraps ProjectService)
    # ------------------------------------------------------------------

    def ensure_mc_project(self, project_service: Any) -> None:
        """Create the Mission Control project if it does not exist."""
        self.project_service = project_service
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
        top_level_only: bool = False,
    ) -> list[dict]:
        tasks = project_service.list_tasks(
            MC_TENANT, MC_PROJECT_ID, status=status,
            top_level_only=top_level_only,
        )
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
        task["steps"] = self.get_task_steps(task_id)
        return self._normalize_task(task)

    def clean_casual_tasks(self, project_service: Any) -> int:
        """Delete auto-created tasks that were casual messages (not real tasks).

        Returns the number of tasks deleted.
        """
        tasks = project_service.list_tasks(MC_TENANT, MC_PROJECT_ID)
        deleted = 0
        for t in tasks:
            desc = t.get("description", "")
            title = t.get("title", "")
            # Only target auto-created tasks
            if "Auto-created from chat message" not in desc:
                continue
            # Check if the title looks like a casual message
            if _NOT_TASK_PATTERNS.match(title.rstrip("...")):
                tid = t["task_id"]
                self.delete_task(project_service, tid)
                deleted += 1
        return deleted

    def cleanup_orphaned_tasks(self, project_service: Any) -> int:
        """Delete stale auto-created tasks that pollute the board.

        Targets:
        1. Tasks whose title matches casual/greeting patterns.
        2. Auto-created tasks (description contains 'Auto-created from chat
           message') that are in 'done' or 'backlog' status.

        Returns the number of tasks deleted.
        """
        tasks = project_service.list_tasks(MC_TENANT, MC_PROJECT_ID)
        deleted = 0
        for t in tasks:
            desc = t.get("description") or ""
            title = t.get("title") or ""
            status = t.get("status") or ""

            # 1) Title matches a casual/greeting pattern
            if _NOT_TASK_PATTERNS.match(title.rstrip("...")):
                self.delete_task(project_service, t["task_id"])
                deleted += 1
                continue

            # 2) Auto-created + terminal/stale status
            if "Auto-created from chat message" in desc and status in ("done", "backlog"):
                self.delete_task(project_service, t["task_id"])
                deleted += 1
                continue

        return deleted

    def create_task(
        self,
        project_service: Any,
        title: str,
        description: str | None = None,
        status: str = "backlog",
        priority: str = "medium",
        assignees: list[str] | None = None,
        owner_agent_id: str | None = None,
        parent_task_id: str | None = None,
    ) -> dict:
        task = project_service.create_task(
            tenant_id=MC_TENANT,
            project_id=MC_PROJECT_ID,
            title=title,
            description=description,
            status=status,
            priority=priority,
            owner_agent_id=owner_agent_id,
            parent_task_id=parent_task_id,
        )
        tid = task["task_id"]
        if assignees:
            with self.db.transaction() as conn:
                for bid in assignees:
                    conn.execute(
                        "INSERT OR IGNORE INTO mc_task_assignments (task_id, being_id) VALUES (?,?)",
                        (tid, bid),
                    )
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
            self.db.execute_commit(
                f"UPDATE project_tasks SET {', '.join(sets)} WHERE task_id = ? AND tenant_id = ?",
                params,
            )
            task = project_service.get_task(MC_TENANT, task_id)

        if assignees is not None:
            with self.db.transaction() as conn:
                conn.execute("DELETE FROM mc_task_assignments WHERE task_id = ?", (task_id,))
                for bid in assignees:
                    conn.execute(
                        "INSERT OR IGNORE INTO mc_task_assignments (task_id, being_id) VALUES (?,?)",
                        (task_id, bid),
                    )
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
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM project_tasks WHERE tenant_id = ? AND task_id = ?",
                (MC_TENANT, task_id),
            )
            conn.execute("DELETE FROM mc_task_assignments WHERE task_id = ?", (task_id,))
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
        self.db.execute_commit(
            "INSERT INTO mc_task_history (id,task_id,action,details,timestamp) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), task_id, action, json.dumps(details), self._now()),
        )

    # ------------------------------------------------------------------
    # Orchestration — parent/child task views
    # ------------------------------------------------------------------

    def get_task_children(self, task_id: str) -> list[str]:
        """Return child task IDs that have this task as parent_task_id."""
        rows = self.db.execute(
            """SELECT task_id FROM project_tasks
               WHERE parent_task_id = ? AND tenant_id = ?
               ORDER BY created_at ASC""",
            (task_id, MC_TENANT),
        ).fetchall()
        return [str(r["task_id"]) for r in rows]

    def get_task_parent(self, task_id: str) -> str | None:
        """Return the parent task ID if this task has one."""
        row = self.db.execute(
            """SELECT parent_task_id FROM project_tasks
               WHERE task_id = ? AND tenant_id = ?
               LIMIT 1""",
            (task_id, MC_TENANT),
        ).fetchone()
        if row is None:
            return None
        ptid = row["parent_task_id"]
        return str(ptid) if ptid is not None else None

    def get_task_with_orchestration(
        self,
        project_service: Any,
        task_id: str,
    ) -> dict:
        """Get a task enriched with orchestration data (children, parent, orch log)."""
        task = self.get_task(project_service, task_id)
        # Add parent/child info
        task["parent_task_id"] = self.get_task_parent(task_id)
        child_ids = self.get_task_children(task_id)
        task["children"] = []
        for cid in child_ids:
            try:
                child = self.get_task(project_service, cid)
                task["children"].append(child)
            except Exception:
                task["children"].append({"id": cid, "status": "unknown"})
        # Add orchestration log if this is an orchestrated task
        task["orchestration_log"] = self.get_orchestration_log(task_id)
        # Add orchestration status if active
        orch_status = self.get_orchestration_status(task_id)
        task["orchestration_status"] = orch_status
        return task

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
        self.db.execute_commit(
            "INSERT INTO mc_events (event_type, payload, created_at) VALUES (?,?,?)",
            (event_type, json.dumps(payload, default=str), now),
        )

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
        "FORMULA.md", "PRIORITIES.md", "REPRESENTATION.md",
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
        # Merge in the per-being skill mapping (artifact skills)
        mapped_skills = self.get_being_skill_list(being.get("id", ""))
        seen = {s.get("name") for s in skills_list}
        for ms in mapped_skills:
            if ms["skill_id"] not in seen:
                skills_list.append({
                    "name": ms["skill_id"],
                    "description": ms.get("description", ""),
                    "path": None,
                })

        # ── 5. Workspace file tree ───────────────────────────────
        file_tree = self._build_file_tree(ws_abs, max_depth=2) if ws_exists else []

        # ── 6. Representation (live from disk) ────────────────────
        representation_text = None
        if ws_exists:
            rep_path = ws_abs / "REPRESENTATION.md"
            if rep_path.is_file():
                try:
                    representation_text = rep_path.read_text(encoding="utf-8")
                except OSError:
                    pass

        # ── 6b. ACT-I architecture (beings + clusters for this sister) ──
        acti_profile = None
        sister_id_for_acti = being_id
        # Map being IDs to sister IDs (e.g. "sai-forge" -> "forge")
        if being_id.startswith("sai-"):
            sister_id_for_acti = being_id[4:]  # strip "sai-" prefix
        if being_id == "prime":
            sister_id_for_acti = "prime"
        try:
            profile = get_sister_profile(sister_id_for_acti)
            if profile["beings"]:
                acti_profile = {
                    "beings": [
                        {
                            "id": b["id"],
                            "name": b["name"],
                            "positions": b["positions"],
                            "domain": b["domain"],
                            "levers": b["levers"],
                            "clusters": b["clusters"],
                        }
                        for b in profile["beings"]
                    ],
                    "clusters": profile["clusters"],
                    "levers": profile["levers"],
                    "positions_total": profile["positions_total"],
                    "shared_heart_skills": [s["name"] for s in SHARED_HEART_SKILLS],
                }
        except Exception:
            pass

        # ── 6c. ACT-I being detail (for type=acti beings) ─────────
        acti_being = None
        if being.get("type") == TYPE_ACTI:
            try:
                from bomba_sr.acti.loader import load_beings as _load_acti, SHARED_HEART_SKILLS as _HS
                for ab in _load_acti():
                    if ab["id"] == being_id:
                        acti_being = {
                            "acti_id": ab.get("acti_id", ""),
                            "domain": ab.get("domain", ""),
                            "positions": ab.get("positions", 0),
                            "levers": ab.get("levers", []),
                            "clusters": ab.get("clusters", []),
                            "shared_heart_skills": [s["name"] for s in _HS],
                            "sister_id": ab.get("sister_id", ""),
                        }
                        break
            except Exception:
                pass

        # ── 7. Dream logs (sai-memory only) ───────────────────────
        dream_logs: list[dict] | None = None
        if being_id == "sai-memory":
            try:
                from bomba_sr.memory.dreaming import DreamCycle
                dream_logs = DreamCycle.list_dream_logs(limit=10)
            except Exception:
                dream_logs = []

        result_dict: dict[str, Any] = {
            "being": being,
            "identity": identity,
            "memory": memory_info,
            "tools": tools_list,
            "skills": skills_list,
            "file_tree": file_tree,
            "representation": representation_text,
            "acti": acti_profile,
        }
        if dream_logs is not None:
            result_dict["dream_logs"] = dream_logs
        if acti_being is not None:
            result_dict["acti_being"] = acti_being
        return result_dict

    def get_acti_architecture(self) -> dict:
        """Return the full ACT-I architecture for the dashboard."""
        return get_full_architecture()

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

    def _normalize_task(self, task: dict) -> dict:
        """Map ProjectService field names to the shape the frontend expects.

        Backend returns: task_id, created_at, updated_at
        Frontend expects: id, created, updated
        Also enriches with steps if they exist.
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
        # Enrich with steps if present
        if "steps" not in t:
            task_id = t.get("id") or t.get("task_id")
            if task_id:
                t["steps"] = self.get_task_steps(task_id)
        # Enrich with artifacts if present
        if "artifacts" not in t:
            task_id = t.get("id") or t.get("task_id")
            if task_id:
                t["artifacts"] = self.list_task_artifacts(task_id)
        return t

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
