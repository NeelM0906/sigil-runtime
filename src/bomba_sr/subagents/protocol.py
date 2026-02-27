from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from bomba_sr.storage.db import RuntimeDB, dict_from_row


VALID_PRIORITIES = {"low", "normal", "high"}
VALID_CLEANUP = {"keep", "archive"}
VALID_SCOPES = {"scratch", "proposal", "committed"}

STATUS_ACCEPTED = "accepted"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"
STATUS_TIMED_OUT = "timed_out"
STATUS_COMPLETED = "completed"

TERMINAL_STATUSES = {STATUS_FAILED, STATUS_TIMED_OUT, STATUS_COMPLETED}


@dataclass(frozen=True)
class SubAgentTask:
    task_id: str
    ticket_id: str
    idempotency_key: str
    goal: str
    done_when: tuple[str, ...]
    input_context_refs: tuple[str, ...]
    output_schema: dict[str, Any]
    priority: str = "normal"
    run_timeout_seconds: int = 600
    cleanup: str = "keep"

    def validate(self) -> None:
        if not self.idempotency_key or len(self.idempotency_key) < 12:
            raise ValueError("idempotency_key must be at least 12 chars")
        if not self.goal.strip():
            raise ValueError("goal is required")
        if not self.done_when:
            raise ValueError("done_when cannot be empty")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError("invalid priority")
        if self.cleanup not in VALID_CLEANUP:
            raise ValueError("invalid cleanup")
        if not (5 <= self.run_timeout_seconds <= 86400):
            raise ValueError("run_timeout_seconds must be between 5 and 86400")


class SubAgentProtocol:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS subagent_runs (
              run_id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              ticket_id TEXT NOT NULL,
              parent_run_id TEXT,
              parent_session_id TEXT NOT NULL,
              parent_turn_id TEXT NOT NULL,
              parent_agent_id TEXT NOT NULL,
              child_agent_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              goal TEXT NOT NULL,
              done_when TEXT NOT NULL,
              input_context_refs TEXT NOT NULL,
              output_schema TEXT NOT NULL,
              priority TEXT NOT NULL,
              run_timeout_seconds INTEGER NOT NULL,
              cleanup TEXT NOT NULL,
              status TEXT NOT NULL,
              progress_pct INTEGER,
              accepted_at TEXT NOT NULL,
              started_at TEXT,
              ended_at TEXT,
              runtime_ms INTEGER,
              token_usage TEXT,
              error_detail TEXT,
              artifacts TEXT,
              UNIQUE(parent_turn_id, idempotency_key),
              FOREIGN KEY(parent_run_id) REFERENCES subagent_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS subagent_events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              run_id TEXT NOT NULL,
              ticket_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              status TEXT NOT NULL,
              progress_pct INTEGER,
              summary TEXT,
              artifacts TEXT,
              runtime_ms INTEGER,
              token_usage TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES subagent_runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS shared_working_memory_writes (
              write_id TEXT PRIMARY KEY,
              run_id TEXT,
              writer_agent_id TEXT NOT NULL,
              ticket_id TEXT NOT NULL,
              scope TEXT NOT NULL,
              confidence REAL NOT NULL,
              content TEXT NOT NULL,
              source_refs TEXT NOT NULL,
              merged_by_agent_id TEXT,
              merged_at TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES subagent_runs(run_id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_subagent_runs_parent
              ON subagent_runs(parent_run_id, status, accepted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_subagent_events_run
              ON subagent_events(run_id, seq ASC);
            CREATE INDEX IF NOT EXISTS idx_shared_writes_ticket
              ON shared_working_memory_writes(ticket_id, created_at DESC);
            """
        )
        self.db.commit()

    def spawn(
        self,
        task: SubAgentTask,
        parent_session_id: str,
        parent_turn_id: str,
        parent_agent_id: str,
        child_agent_id: str,
        parent_run_id: str | None = None,
    ) -> dict[str, Any]:
        task.validate()
        now = self._now()
        run_id = str(uuid.uuid4())
        try:
            self.db.execute(
                """
                INSERT INTO subagent_runs (
                  run_id, task_id, ticket_id, parent_run_id, parent_session_id, parent_turn_id,
                  parent_agent_id, child_agent_id, idempotency_key, goal, done_when,
                  input_context_refs, output_schema, priority, run_timeout_seconds, cleanup,
                  status, accepted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task.task_id,
                    task.ticket_id,
                    parent_run_id,
                    parent_session_id,
                    parent_turn_id,
                    parent_agent_id,
                    child_agent_id,
                    task.idempotency_key,
                    task.goal,
                    json.dumps(list(task.done_when)),
                    json.dumps(list(task.input_context_refs)),
                    json.dumps(task.output_schema),
                    task.priority,
                    task.run_timeout_seconds,
                    task.cleanup,
                    STATUS_ACCEPTED,
                    now,
                ),
            )
            self._add_event(
                run_id=run_id,
                ticket_id=task.ticket_id,
                event_type="accepted",
                status=STATUS_ACCEPTED,
                summary="Sub-agent run accepted",
            )
            self.db.commit()
            return self.get_run(run_id)
        except sqlite3.IntegrityError:
            # Idempotent replay: return existing run.
            row = self.db.execute(
                "SELECT run_id FROM subagent_runs WHERE parent_turn_id = ? AND idempotency_key = ?",
                (parent_turn_id, task.idempotency_key),
            ).fetchone()
            if row is None:
                raise
            return self.get_run(str(row["run_id"]))

    def start(self, run_id: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] != STATUS_ACCEPTED:
            raise ValueError("run must be accepted before start")
        now = self._now()
        self.db.execute(
            "UPDATE subagent_runs SET status = ?, started_at = ? WHERE run_id = ?",
            (STATUS_IN_PROGRESS, now, run_id),
        )
        self._add_event(run_id, run["ticket_id"], "started", STATUS_IN_PROGRESS, summary="Run started")
        self.db.commit()
        return self.get_run(run_id)

    def progress(self, run_id: str, progress_pct: int, summary: str | None = None, artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
        if not (0 <= progress_pct <= 100):
            raise ValueError("progress_pct must be 0-100")
        run = self._require_run(run_id)
        if run["status"] not in {STATUS_IN_PROGRESS, STATUS_BLOCKED}:
            raise ValueError("run must be in progress or blocked for progress updates")

        self.db.execute(
            "UPDATE subagent_runs SET status = ?, progress_pct = ?, artifacts = COALESCE(?, artifacts) WHERE run_id = ?",
            (
                STATUS_IN_PROGRESS,
                progress_pct,
                json.dumps(artifacts) if artifacts is not None else None,
                run_id,
            ),
        )
        self._add_event(
            run_id,
            run["ticket_id"],
            "progress",
            STATUS_IN_PROGRESS,
            progress_pct=progress_pct,
            summary=summary,
            artifacts=artifacts,
        )
        self.db.commit()
        return self.get_run(run_id)

    def block(self, run_id: str, reason: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] in TERMINAL_STATUSES:
            return self.get_run(run_id)
        self.db.execute(
            "UPDATE subagent_runs SET status = ?, error_detail = ? WHERE run_id = ?",
            (STATUS_BLOCKED, reason, run_id),
        )
        self._add_event(run_id, run["ticket_id"], "blocked", STATUS_BLOCKED, summary=reason)
        self.db.commit()
        return self.get_run(run_id)

    def fail(self, run_id: str, reason: str) -> dict[str, Any]:
        return self._finish(
            run_id=run_id,
            status=STATUS_FAILED,
            event_type="failed",
            summary=reason,
            error_detail=reason,
        )

    def timeout(self, run_id: str, reason: str = "timed out") -> dict[str, Any]:
        return self._finish(
            run_id=run_id,
            status=STATUS_TIMED_OUT,
            event_type="timed_out",
            summary=reason,
            error_detail=reason,
        )

    def complete(
        self,
        run_id: str,
        summary: str,
        artifacts: dict[str, Any] | None,
        runtime_ms: int,
        token_usage: dict[str, int] | None,
    ) -> dict[str, Any]:
        return self._finish(
            run_id=run_id,
            status=STATUS_COMPLETED,
            event_type="completed",
            summary=summary,
            artifacts=artifacts,
            runtime_ms=runtime_ms,
            token_usage=token_usage,
        )

    def _finish(
        self,
        run_id: str,
        status: str,
        event_type: str,
        summary: str,
        artifacts: dict[str, Any] | None = None,
        runtime_ms: int | None = None,
        token_usage: dict[str, int] | None = None,
        error_detail: str | None = None,
    ) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] in TERMINAL_STATUSES:
            return self.get_run(run_id)

        ended_at = self._now()
        self.db.execute(
            """
            UPDATE subagent_runs
            SET status = ?, ended_at = ?, runtime_ms = ?, token_usage = ?, error_detail = ?, artifacts = COALESCE(?, artifacts)
            WHERE run_id = ?
            """,
            (
                status,
                ended_at,
                runtime_ms,
                json.dumps(token_usage) if token_usage is not None else None,
                error_detail,
                json.dumps(artifacts) if artifacts is not None else None,
                run_id,
            ),
        )
        self._add_event(
            run_id,
            run["ticket_id"],
            event_type,
            status,
            summary=summary,
            runtime_ms=runtime_ms,
            artifacts=artifacts,
            token_usage=token_usage,
        )
        self.db.commit()
        return self.get_run(run_id)

    def write_shared_memory(
        self,
        run_id: str | None,
        writer_agent_id: str,
        ticket_id: str,
        scope: str,
        confidence: float,
        content: str,
        source_refs: list[str] | None = None,
    ) -> str:
        if scope not in VALID_SCOPES:
            raise ValueError("invalid scope")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if not content.strip():
            raise ValueError("content cannot be empty")

        write_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO shared_working_memory_writes (
              write_id, run_id, writer_agent_id, ticket_id, scope, confidence, content,
              source_refs, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                write_id,
                run_id,
                writer_agent_id,
                ticket_id,
                scope,
                confidence,
                content,
                json.dumps(source_refs or []),
                self._now(),
            ),
        )
        self.db.commit()
        return write_id

    def promote_shared_write(self, write_id: str, merged_by_agent_id: str) -> None:
        self.db.execute(
            """
            UPDATE shared_working_memory_writes
            SET scope = 'committed', merged_by_agent_id = ?, merged_at = ?
            WHERE write_id = ?
            """,
            (merged_by_agent_id, self._now(), write_id),
        )
        self.db.commit()

    def stream_events(self, run_id: str, after_seq: int = 0) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM subagent_events WHERE run_id = ? AND seq > ? ORDER BY seq ASC",
            (run_id, after_seq),
        ).fetchall()
        return [self._event_row_to_dict(dict_from_row(row) or {}) for row in rows]

    def cascade_stop(self, root_run_id: str, reason: str = "cascade stop") -> list[str]:
        stopped: list[str] = []
        queue = [root_run_id]
        while queue:
            current = queue.pop(0)
            run = self.get_run(current)
            if run is None:
                continue
            queue.extend(self._children_of(current))
            if run["status"] in TERMINAL_STATUSES:
                continue
            self.timeout(current, reason=reason)
            stopped.append(current)
        return stopped

    def announce_with_retry(
        self,
        run_id: str,
        sender: Callable[[dict[str, Any]], bool],
        max_attempts: int = 3,
        base_delay_seconds: float = 0.1,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> bool:
        run = self.get_run(run_id)
        if run is None:
            raise ValueError("run not found")

        payload = {
            "runId": run["run_id"],
            "ticketId": run["ticket_id"],
            "status": run["status"],
            "summary": run.get("error_detail") or "Sub-agent completed",
            "runtimeMs": run.get("runtime_ms"),
            "tokenUsage": run.get("token_usage"),
        }

        for attempt in range(max_attempts):
            ok = bool(sender(payload))
            if ok:
                self._add_event(
                    run_id=run["run_id"],
                    ticket_id=run["ticket_id"],
                    event_type="announced",
                    status=run["status"],
                    summary=f"announce success after {attempt + 1} attempt(s)",
                )
                self.db.commit()
                return True
            if attempt < max_attempts - 1:
                sleep_fn(base_delay_seconds * (2 ** attempt))

        self._add_event(
            run_id=run["run_id"],
            ticket_id=run["ticket_id"],
            event_type="announced",
            status=run["status"],
            summary=f"announce failed after {max_attempts} attempt(s)",
        )
        self.db.commit()
        return False

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM subagent_runs WHERE run_id = ?", (run_id,)).fetchone()
        record = dict_from_row(row)
        if record is None:
            return None
        return self._run_row_to_dict(record)

    def _children_of(self, run_id: str) -> list[str]:
        rows = self.db.execute(
            "SELECT run_id FROM subagent_runs WHERE parent_run_id = ?",
            (run_id,),
        ).fetchall()
        return [str(r["run_id"]) for r in rows]

    def _require_run(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        return run

    def _add_event(
        self,
        run_id: str,
        ticket_id: str,
        event_type: str,
        status: str,
        progress_pct: int | None = None,
        summary: str | None = None,
        artifacts: dict[str, Any] | None = None,
        runtime_ms: int | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO subagent_events (
              event_id, run_id, ticket_id, event_type, status, progress_pct,
              summary, artifacts, runtime_ms, token_usage, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                run_id,
                ticket_id,
                event_type,
                status,
                progress_pct,
                summary,
                json.dumps(artifacts) if artifacts is not None else None,
                runtime_ms,
                json.dumps(token_usage) if token_usage is not None else None,
                self._now(),
            ),
        )

    @staticmethod
    def _run_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        for key in ("done_when", "input_context_refs", "output_schema", "token_usage", "artifacts"):
            value = out.get(key)
            if isinstance(value, str) and value:
                try:
                    out[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return out

    @staticmethod
    def _event_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        for key in ("artifacts", "token_usage"):
            value = out.get(key)
            if isinstance(value, str) and value:
                try:
                    out[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return out

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
