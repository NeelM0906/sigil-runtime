from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from bomba_sr.storage.db import RuntimeDB, dict_from_row

try:  # pragma: no cover - optional dependency in some dev environments
    from croniter import croniter as _croniter
except Exception:  # pragma: no cover
    _croniter = None


ScheduledRunner = Callable[[str, str], dict[str, Any] | None]


class CronScheduler:
    def __init__(
        self,
        db: RuntimeDB,
        tenant_id: str,
        user_id: str,
        runner: ScheduledRunner,
        poll_interval_seconds: int = 15,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.runner = runner
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ensure_schema()

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"bomba-cron-{self.tenant_id}",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._thread = None

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def status(self) -> dict[str, Any]:
        return {
            "running": self.is_running(),
            "poll_interval_seconds": self.poll_interval_seconds,
            "scheduled_count": len(self.list_tasks(include_disabled=True)),
        }

    def add_task(
        self,
        cron_expression: str,
        task_goal: str,
        enabled: bool = True,
        *,
        schedule_type: str = "cron",
        run_at: str | None = None,
        interval_seconds: int | None = None,
        delete_after_run: bool = False,
    ) -> dict[str, Any]:
        goal = task_goal.strip()
        if not goal:
            raise ValueError("task_goal must not be empty")

        schedule_type = schedule_type.strip().lower()
        if schedule_type not in ("cron", "at", "every"):
            raise ValueError(f"schedule_type must be 'cron', 'at', or 'every', got: {schedule_type!r}")

        now = datetime.now(timezone.utc)

        # Determine cron_expression and next_run based on schedule_type
        if schedule_type == "at":
            if not run_at:
                raise ValueError("run_at is required for schedule_type='at'")
            next_run = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)
            expression = run_at
            # One-shot tasks default to delete_after_run=True unless explicitly set
            delete_after_run = True
        elif schedule_type == "every":
            if not interval_seconds or interval_seconds < 1:
                raise ValueError("interval_seconds must be >= 1 for schedule_type='every'")
            next_run = now + timedelta(seconds=interval_seconds)
            expression = f"every:{interval_seconds}s"
        else:
            # cron
            expression = cron_expression.strip()
            if not expression:
                raise ValueError("cron_expression must not be empty for schedule_type='cron'")
            next_run = self._next_from_expression(expression, now)

        task_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO scheduled_tasks (
              id, tenant_id, user_id, cron_expression, task_goal, enabled,
              last_run_at, next_run_at, created_at,
              schedule_type, delete_after_run, interval_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                self.tenant_id,
                self.user_id,
                expression,
                goal,
                int(bool(enabled)),
                next_run.isoformat(),
                now.isoformat(),
                schedule_type,
                int(bool(delete_after_run)),
                interval_seconds,
            ),
        )
        self.db.commit()
        return {
            "id": task_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "schedule_type": schedule_type,
            "cron_expression": expression,
            "task_goal": goal,
            "enabled": bool(enabled),
            "next_run_at": next_run.isoformat(),
            "delete_after_run": delete_after_run,
            "interval_seconds": interval_seconds,
        }

    def list_tasks(self, include_disabled: bool = True) -> list[dict[str, Any]]:
        if include_disabled:
            rows = self.db.execute(
                """
                SELECT *
                FROM scheduled_tasks
                WHERE tenant_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (self.tenant_id, self.user_id),
            ).fetchall()
        else:
            rows = self.db.execute(
                """
                SELECT *
                FROM scheduled_tasks
                WHERE tenant_id = ? AND user_id = ? AND enabled = 1
                ORDER BY created_at DESC
                """,
                (self.tenant_id, self.user_id),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict_from_row(row)
            item["enabled"] = bool(item.get("enabled"))
            item["delete_after_run"] = bool(item.get("delete_after_run"))
            out.append(item)
        return out

    def remove_task(self, task_id: str) -> dict[str, Any]:
        deleted = self.db.execute(
            "DELETE FROM scheduled_tasks WHERE tenant_id = ? AND user_id = ? AND id = ?",
            (self.tenant_id, self.user_id, task_id),
        ).rowcount
        self.db.commit()
        return {"removed": bool(deleted), "task_id": task_id}

    def set_enabled(self, task_id: str, enabled: bool) -> dict[str, Any]:
        updated = self.db.execute(
            "UPDATE scheduled_tasks SET enabled = ? WHERE tenant_id = ? AND user_id = ? AND id = ?",
            (int(bool(enabled)), self.tenant_id, self.user_id, task_id),
        ).rowcount
        self.db.commit()
        return {"updated": bool(updated), "task_id": task_id, "enabled": bool(enabled)}

    def get_runs(self, task_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent run history, optionally filtered by task_id."""
        if task_id:
            rows = self.db.execute(
                """
                SELECT * FROM scheduled_task_runs
                WHERE tenant_id = ? AND task_id = ?
                ORDER BY ran_at DESC LIMIT ?
                """,
                (self.tenant_id, task_id, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                """
                SELECT * FROM scheduled_task_runs
                WHERE tenant_id = ?
                ORDER BY ran_at DESC LIMIT ?
                """,
                (self.tenant_id, limit),
            ).fetchall()
        return [dict_from_row(r) for r in rows]

    def _record_run(
        self,
        task_id: str,
        ran_at: datetime,
        status: str,
        result_payload: dict[str, Any],
    ) -> None:
        """Insert a row into the run history table."""
        run_id = str(uuid.uuid4())
        error_message = result_payload.get("error") if status == "error" else None
        self.db.execute(
            """
            INSERT INTO scheduled_task_runs (
              id, tenant_id, task_id, ran_at, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, self.tenant_id, task_id, ran_at.isoformat(), status, error_message),
        )

    def run_due_once(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        rows = self.db.execute(
            """
            SELECT *
            FROM scheduled_tasks
            WHERE tenant_id = ? AND user_id = ? AND enabled = 1 AND next_run_at <= ?
            ORDER BY next_run_at ASC
            """,
            (self.tenant_id, self.user_id, now.isoformat()),
        ).fetchall()
        results: list[dict[str, Any]] = []
        tasks_to_delete: list[str] = []
        for row in rows:
            item = dict_from_row(row)
            task_id = str(item["id"])
            expression = str(item["cron_expression"])
            goal = str(item["task_goal"])
            sched_type = str(item.get("schedule_type") or "cron")
            delete_flag = bool(item.get("delete_after_run"))
            interval_secs = item.get("interval_seconds")

            result_payload: dict[str, Any] = {}
            status = "ok"
            try:
                result_payload = self.runner(goal, task_id) or {}
            except Exception as exc:
                result_payload = {"error": str(exc)}
                status = "error"

            # Record the run
            self._record_run(task_id, now, status, result_payload)

            # Compute next_run based on schedule_type
            if sched_type == "at":
                # One-shot: disable and optionally delete
                tasks_to_delete.append(task_id)
                next_run_iso = None
            elif sched_type == "every" and interval_secs:
                next_run = now + timedelta(seconds=int(interval_secs))
                next_run_iso = next_run.isoformat()
            else:
                # cron
                next_run = self._next_from_expression(expression, now)
                next_run_iso = next_run.isoformat()

            if next_run_iso and not delete_flag:
                self.db.execute(
                    """
                    UPDATE scheduled_tasks
                    SET last_run_at = ?, next_run_at = ?
                    WHERE id = ?
                    """,
                    (now.isoformat(), next_run_iso, task_id),
                )
            elif delete_flag or sched_type == "at":
                tasks_to_delete.append(task_id)

            results.append(
                {
                    "task_id": task_id,
                    "ran_at": now.isoformat(),
                    "next_run_at": next_run_iso,
                    "status": status,
                    "result": result_payload,
                    "deleted": task_id in tasks_to_delete,
                }
            )

        # Delete one-shot tasks that have fired
        for tid in set(tasks_to_delete):
            self.db.execute(
                "DELETE FROM scheduled_tasks WHERE id = ?",
                (tid,),
            )

        if rows:
            self.db.commit()
        return results

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_interval_seconds):
            self.run_due_once()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              cron_expression TEXT NOT NULL,
              task_goal TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              last_run_at TEXT,
              next_run_at TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_due
              ON scheduled_tasks(tenant_id, user_id, enabled, next_run_at);

            CREATE TABLE IF NOT EXISTS scheduled_task_runs (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              task_id TEXT NOT NULL,
              ran_at TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'ok',
              error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_scheduled_task_runs_task
              ON scheduled_task_runs(tenant_id, task_id, ran_at);
            """
        )
        self.db.commit()
        # Add columns that may not exist in older schemas
        for col, col_type, default in [
            ("schedule_type", "TEXT", "'cron'"),
            ("delete_after_run", "INTEGER", "0"),
            ("interval_seconds", "INTEGER", "NULL"),
        ]:
            try:
                self.db.execute(
                    f"ALTER TABLE scheduled_tasks ADD COLUMN {col} {col_type} DEFAULT {default}"
                )
                self.db.commit()
            except Exception:
                pass  # column already exists

    @staticmethod
    def _next_from_expression(cron_expression: str, base_time: datetime) -> datetime:
        if _croniter is not None:
            return _croniter(cron_expression, base_time).get_next(datetime)

        expr = cron_expression.strip()
        if expr == "@hourly":
            return base_time + timedelta(hours=1)
        if expr == "@daily":
            return base_time + timedelta(days=1)
        if expr.startswith("*/"):
            parts = expr.split()
            if len(parts) == 5 and parts[0].startswith("*/"):
                try:
                    minutes = int(parts[0][2:])
                    minutes = max(1, minutes)
                except ValueError as exc:
                    raise ValueError(f"unsupported cron expression: {cron_expression}") from exc
                return base_time + timedelta(minutes=minutes)
        parts = expr.split()
        if len(parts) == 5 and parts[0].isdigit():
            minute = int(parts[0])
            if not (0 <= minute <= 59):
                raise ValueError(f"unsupported cron expression: {cron_expression}")
            next_hour = (base_time + timedelta(hours=1)).replace(minute=minute, second=0, microsecond=0)
            return next_hour
        raise ValueError(
            "croniter is unavailable and cron expression is unsupported. "
            "Install croniter or use @hourly, @daily, */N * * * *, or M * * * *."
        )
