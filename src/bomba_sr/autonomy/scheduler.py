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

    def add_task(self, cron_expression: str, task_goal: str, enabled: bool = True) -> dict[str, Any]:
        expression = cron_expression.strip()
        if not expression:
            raise ValueError("cron_expression must not be empty")
        goal = task_goal.strip()
        if not goal:
            raise ValueError("task_goal must not be empty")

        now = datetime.now(timezone.utc)
        next_run = self._next_from_expression(expression, now)
        task_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO scheduled_tasks (
              id, tenant_id, user_id, cron_expression, task_goal, enabled, last_run_at, next_run_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
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
            ),
        )
        self.db.commit()
        return {
            "id": task_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "cron_expression": expression,
            "task_goal": goal,
            "enabled": bool(enabled),
            "next_run_at": next_run.isoformat(),
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
        for row in rows:
            item = dict_from_row(row)
            task_id = str(item["id"])
            expression = str(item["cron_expression"])
            goal = str(item["task_goal"])
            result_payload: dict[str, Any] = {}
            try:
                result_payload = self.runner(goal, task_id) or {}
            except Exception as exc:
                result_payload = {"error": str(exc)}
            next_run = self._next_from_expression(expression, now)
            self.db.execute(
                """
                UPDATE scheduled_tasks
                SET last_run_at = ?, next_run_at = ?
                WHERE id = ?
                """,
                (now.isoformat(), next_run.isoformat(), task_id),
            )
            results.append(
                {
                    "task_id": task_id,
                    "ran_at": now.isoformat(),
                    "next_run_at": next_run.isoformat(),
                    "result": result_payload,
                }
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
            """
        )
        self.db.commit()

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
