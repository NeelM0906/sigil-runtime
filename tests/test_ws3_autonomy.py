from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bomba_sr.autonomy.heartbeat import HeartbeatEngine
from bomba_sr.autonomy.scheduler import CronScheduler
from bomba_sr.storage.db import RuntimeDB


class AutonomyTests(unittest.TestCase):
    def test_heartbeat_run_once_reads_file_and_invokes_runner(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "HEARTBEAT.md").write_text("# Heartbeat\n- [ ] check status\n", encoding="utf-8")
            calls: list[str] = []

            def runner(content: str):
                calls.append(content)
                return {"assistant_text": "all clear"}

            engine = HeartbeatEngine(
                tenant_id="t1",
                user_id="u1",
                workspace_root=workspace,
                runner=runner,
                interval_seconds=999,
            )
            result = engine.run_once()
            self.assertTrue(result["ran"])
            self.assertEqual(len(calls), 1)
            self.assertIn("check status", calls[0])
            status = engine.status()
            self.assertEqual(status["runs"], 1)

    def test_cron_scheduler_add_list_run_due_enable_disable_remove(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            calls: list[tuple[str, str]] = []

            def runner(task_goal: str, task_id: str):
                calls.append((task_id, task_goal))
                return {"ok": True}

            scheduler = CronScheduler(
                db=db,
                tenant_id="t1",
                user_id="u1",
                runner=runner,
                poll_interval_seconds=999,
            )
            created = scheduler.add_task("*/1 * * * *", "ping workspace", enabled=True)
            self.assertIn("id", created)

            rows = scheduler.list_tasks()
            self.assertEqual(len(rows), 1)
            task_id = str(rows[0]["id"])

            past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
            db.execute("UPDATE scheduled_tasks SET next_run_at = ? WHERE id = ?", (past, task_id))
            db.commit()

            due_results = scheduler.run_due_once()
            self.assertEqual(len(due_results), 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], task_id)

            disabled = scheduler.set_enabled(task_id, enabled=False)
            self.assertTrue(disabled["updated"])
            enabled_rows = scheduler.list_tasks(include_disabled=False)
            self.assertEqual(enabled_rows, [])

            removed = scheduler.remove_task(task_id)
            self.assertTrue(removed["removed"])
            self.assertEqual(scheduler.list_tasks(), [])


if __name__ == "__main__":
    unittest.main()
