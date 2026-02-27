from __future__ import annotations

import tempfile
import unittest
import uuid

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.orchestrator import SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask


class SubAgentOrchestratorTests(unittest.TestCase):
    def test_async_worker_runs_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol)

            task = SubAgentTask(
                task_id=str(uuid.uuid4()),
                ticket_id=str(uuid.uuid4()),
                idempotency_key="turn-x::hash-123456",
                goal="Summarize file changes",
                done_when=("summary",),
                input_context_refs=(str(uuid.uuid4()),),
                output_schema={"summary": "string"},
                priority="normal",
                run_timeout_seconds=60,
                cleanup="keep",
            )

            def worker(run_id: str, _task: SubAgentTask, p: SubAgentProtocol) -> dict:
                p.progress(run_id, 50, summary="halfway")
                return {
                    "summary": "done",
                    "runtime_ms": 12,
                    "token_usage": {"input": 10, "output": 4, "total": 14},
                }

            handle = orchestrator.spawn_async(
                task=task,
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-x",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
                worker=worker,
            )
            handle.future.result(timeout=5)

            run = protocol.get_run(handle.run_id)
            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(run["status"], "completed")


if __name__ == "__main__":
    unittest.main()
