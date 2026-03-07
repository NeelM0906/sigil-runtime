from __future__ import annotations

import tempfile
import unittest
import uuid

from bomba_sr.runtime.bridge import TurnRequest
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask
from bomba_sr.subagents.worker import SubAgentWorkerFactory


class SubAgentProtocolTests(unittest.TestCase):
    def _task(self, ticket_id: str, idempotency_key: str) -> SubAgentTask:
        return SubAgentTask(
            tenant_id="tenant-wave2",
            task_id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            idempotency_key=idempotency_key,
            goal="Analyze parser errors",
            done_when=("Root cause identified", "Patch proposed"),
            input_context_refs=(str(uuid.uuid4()),),
            output_schema={"summary": "string", "artifacts": "object"},
            priority="normal",
            run_timeout_seconds=120,
            cleanup="keep",
            workspace_root=None,
            model_id=None,
        )

    def test_idempotent_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)
            ticket = str(uuid.uuid4())
            key = "turn-123::hash-abcde"
            t = self._task(ticket, key)

            first = p.spawn(
                task=t,
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-123",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            second = p.spawn(
                task=t,
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-123",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            self.assertEqual(first["run_id"], second["run_id"])

    def test_lifecycle_and_event_stream(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)

            run = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-456::hash-qwerty"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-456",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            run_id = run["run_id"]

            p.start(run_id)
            p.progress(run_id, 35, summary="Collected traces")
            p.complete(
                run_id,
                summary="Patch ready",
                artifacts={"diff": "..."},
                runtime_ms=950,
                token_usage={"input": 100, "output": 40, "total": 140},
            )

            events = p.stream_events(run_id)
            types = [e["event_type"] for e in events]
            self.assertEqual(types[:4], ["accepted", "started", "progress", "completed"])

    def test_shared_memory_write_and_promote(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)

            run = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-789::hash-zxcvb"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-789",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            write_id = p.write_shared_memory(
                run_id=run["run_id"],
                writer_agent_id=str(uuid.uuid4()),
                ticket_id=run["ticket_id"],
                scope="proposal",
                confidence=0.88,
                content="Root cause likely in parser tokenization",
                source_refs=[str(uuid.uuid4())],
            )
            p.promote_shared_write(write_id, merged_by_agent_id=str(uuid.uuid4()))

            row = db.execute(
                "SELECT scope, merged_by_agent_id FROM shared_working_memory_writes WHERE write_id = ?",
                (write_id,),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["scope"], "committed")
            self.assertTrue(row["merged_by_agent_id"])

    def test_read_shared_memory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)

            run = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-read::hash-read1"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-read",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            ticket = run["ticket_id"]

            # Write two entries: one scratch, one committed
            p.write_shared_memory(
                run_id=run["run_id"],
                writer_agent_id="agent-a",
                ticket_id=ticket,
                scope="scratch",
                confidence=0.5,
                content="Scratch note",
            )
            w2 = p.write_shared_memory(
                run_id=run["run_id"],
                writer_agent_id="agent-b",
                ticket_id=ticket,
                scope="committed",
                confidence=0.9,
                content="Committed finding",
                source_refs=["ref-1", "ref-2"],
            )

            # Read all — should get both
            all_writes = p.read_shared_memory(ticket)
            self.assertEqual(len(all_writes), 2)

            # Read filtered by scope — should get one
            committed = p.read_shared_memory(ticket, scope="committed")
            self.assertEqual(len(committed), 1)
            self.assertEqual(committed[0]["content"], "Committed finding")
            self.assertEqual(committed[0]["scope"], "committed")
            self.assertEqual(committed[0]["source_refs"], ["ref-1", "ref-2"])
            self.assertEqual(committed[0]["write_id"], w2)

            # Read with non-matching scope — empty
            proposals = p.read_shared_memory(ticket, scope="proposal")
            self.assertEqual(len(proposals), 0)

            # Invalid scope raises
            with self.assertRaises(ValueError):
                p.read_shared_memory(ticket, scope="invalid")

    def test_cascade_stop_and_announce_retry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)

            parent = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-parent::hash-aaabb"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-parent",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            child = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-child::hash-cccdd"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-child",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
                parent_run_id=parent["run_id"],
            )

            p.start(parent["run_id"])
            p.start(child["run_id"])

            stopped = p.cascade_stop(parent["run_id"], reason="parent aborted")
            self.assertIn(parent["run_id"], stopped)
            self.assertIn(child["run_id"], stopped)

            # Force one completed run for announce retries.
            done = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-done::hash-eeeff"),
                parent_session_id=str(uuid.uuid4()),
                parent_turn_id="turn-done",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            p.start(done["run_id"])
            p.complete(done["run_id"], summary="done", artifacts=None, runtime_ms=10, token_usage=None)

            attempts = {"n": 0}

            def sender(_payload: dict) -> bool:
                attempts["n"] += 1
                return attempts["n"] >= 3

            ok = p.announce_with_retry(done["run_id"], sender=sender, max_attempts=4, base_delay_seconds=0.001)
            self.assertTrue(ok)
            self.assertEqual(attempts["n"], 3)

    def test_cascade_stop_session_stops_active_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            p = SubAgentProtocol(db)
            session_id = str(uuid.uuid4())

            run_a = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-a::hash-12345"),
                parent_session_id=session_id,
                parent_turn_id="turn-a",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            run_b = p.spawn(
                task=self._task(str(uuid.uuid4()), "turn-b::hash-67890"),
                parent_session_id=session_id,
                parent_turn_id="turn-b",
                parent_agent_id=str(uuid.uuid4()),
                child_agent_id=str(uuid.uuid4()),
            )
            p.start(run_a["run_id"])
            p.start(run_b["run_id"])

            stopped = p.cascade_stop_session("tenant-wave2", session_id, reason="session-ended")
            self.assertIn(run_a["run_id"], stopped)
            self.assertIn(run_b["run_id"], stopped)

    def test_worker_factory_passes_max_loop_iterations(self) -> None:
        class _BridgeStub:
            def __init__(self) -> None:
                self.request: TurnRequest | None = None

            def handle_turn(self, request: TurnRequest) -> dict:
                self.request = request
                return {
                    "assistant": {
                        "text": "done",
                        "loop_iterations": 1,
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                }

        class _ProtocolStub:
            def get_run(self, run_id: str) -> dict | None:  # noqa: ANN001
                return {
                    "run_id": run_id,
                    "parent_agent_id": "prime",
                    "child_agent_id": "forge",
                }

            def progress(self, run_id: str, pct: int, summary: str | None = None) -> None:  # noqa: ANN001
                _ = (run_id, pct, summary)

            def write_shared_memory(self, **kwargs):  # noqa: ANN001
                _ = kwargs

        bridge = _BridgeStub()
        factory = SubAgentWorkerFactory(bridge)
        worker = factory.create_worker(max_iterations=7)
        task = self._task(str(uuid.uuid4()), "turn-worker::hash-11223")
        worker("run-1", task, _ProtocolStub())
        assert bridge.request is not None
        self.assertEqual(bridge.request.max_loop_iterations, 7)
        self.assertEqual(bridge.request.session_id, "subagent:run-1:forge")
        self.assertEqual(bridge.request.user_id, "prime->forge")


if __name__ == "__main__":
    unittest.main()
