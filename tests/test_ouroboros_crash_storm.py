from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.orchestrator import CrashStormConfig, SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask


def _task(i: int) -> SubAgentTask:
    return SubAgentTask(
        tenant_id="tenant-crash",
        task_id=f"task-{i}",
        ticket_id=f"ticket-{i}",
        idempotency_key=f"idem-key-{i}-{uuid.uuid4().hex[:16]}",
        goal="do work",
        done_when=("done",),
        input_context_refs=(),
        output_schema={"summary": "string"},
        priority="normal",
        run_timeout_seconds=30,
        cleanup="keep",
        workspace_root=None,
        model_id=None,
    )


def _failing_worker(run_id, task, protocol):
    raise RuntimeError("boom")


def _ok_worker(run_id, task, protocol):
    return {"summary": "ok", "runtime_ms": 1}


class OuroborosCrashStormTests(unittest.TestCase):
    def test_crash_storm_blocks_new_spawns_until_reset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(Path(td) / "runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(
                protocol=protocol,
                max_workers=2,
                crash_storm_config=CrashStormConfig(window_seconds=60, max_crashes=3, cooldown_seconds=120),
            )

            for i in range(3):
                handle = orchestrator.spawn_async(
                    task=_task(i),
                    parent_session_id="session-1",
                    parent_turn_id=f"turn-{i}",
                    parent_agent_id="parent",
                    child_agent_id="child",
                    worker=_failing_worker,
                )
                with self.assertRaises(RuntimeError):
                    handle.future.result(timeout=2)

            with self.assertRaises(RuntimeError):
                orchestrator.spawn_async(
                    task=_task(100),
                    parent_session_id="session-1",
                    parent_turn_id="turn-100",
                    parent_agent_id="parent",
                    child_agent_id="child",
                    worker=_ok_worker,
                )

            orchestrator.crash_detector.reset()
            handle = orchestrator.spawn_async(
                task=_task(200),
                parent_session_id="session-1",
                parent_turn_id="turn-200",
                parent_agent_id="parent",
                child_agent_id="child",
                worker=_ok_worker,
            )
            result = handle.future.result(timeout=2)
            self.assertEqual(result["summary"], "ok")


if __name__ == "__main__":
    unittest.main()
