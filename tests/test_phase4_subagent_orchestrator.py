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
                tenant_id="tenant-subagents",
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
                workspace_root=None,
                model_id=None,
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

    def test_spawn_depth_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol, max_spawn_depth=2)

            def worker(_run_id: str, _task: SubAgentTask, _p: SubAgentProtocol) -> dict:
                return {"summary": "ok", "runtime_ms": 1}

            root = SubAgentTask(
                tenant_id="tenant-subagents",
                task_id="root",
                ticket_id=str(uuid.uuid4()),
                idempotency_key="turn-root::hash-depth-001",
                goal="root",
                done_when=("done",),
                input_context_refs=(),
                output_schema={"summary": "string"},
            )
            root_handle = orchestrator.spawn_async(
                task=root,
                parent_session_id="session-depth",
                parent_turn_id="turn-root",
                parent_agent_id="parent",
                child_agent_id="child-1",
                worker=worker,
            )
            root_handle.future.result(timeout=3)

            child = SubAgentTask(
                tenant_id="tenant-subagents",
                task_id="child",
                ticket_id=str(uuid.uuid4()),
                idempotency_key="turn-child::hash-depth-002",
                goal="child",
                done_when=("done",),
                input_context_refs=(),
                output_schema={"summary": "string"},
            )
            child_handle = orchestrator.spawn_async(
                task=child,
                parent_session_id="session-depth",
                parent_turn_id="turn-child",
                parent_agent_id="parent",
                child_agent_id="child-2",
                worker=worker,
                parent_run_id=root_handle.run_id,
            )
            child_handle.future.result(timeout=3)

            too_deep = SubAgentTask(
                tenant_id="tenant-subagents",
                task_id="too-deep",
                ticket_id=str(uuid.uuid4()),
                idempotency_key="turn-too-deep::hash-depth-003",
                goal="too-deep",
                done_when=("done",),
                input_context_refs=(),
                output_schema={"summary": "string"},
            )
            with self.assertRaises(RuntimeError):
                orchestrator.spawn_async(
                    task=too_deep,
                    parent_session_id="session-depth",
                    parent_turn_id="turn-too-deep",
                    parent_agent_id="parent",
                    child_agent_id="child-3",
                    worker=worker,
                    parent_run_id=child_handle.run_id,
                )


if __name__ == "__main__":
    unittest.main()
