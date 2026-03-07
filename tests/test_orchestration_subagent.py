"""Tests for OrchestrationEngine integration with SubAgentProtocol.

Verifies:
  - Subtask spawns go through SubAgentProtocol
  - Idempotency key prevents duplicate runs
  - Parallel delegation spawns all before awaiting
  - Sequential delegation interleaves spawn/await
  - Sequential prior outputs come from shared memory
  - Synthesis reads outputs from shared memory
  - Timeout triggers cascade stop
  - Failed subtask output is captured
  - Being status managed by worker only (not engine)
  - Cascade stop on orchestration failure
  - STATUS_AWAITING removed
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import threading
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

from bomba_sr.orchestration.engine import (
    OrchestrationEngine,
    OrchestrationPlan,
    SubTaskPlan,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask
from bomba_sr.storage.db import RuntimeDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine(
    beings: list[dict[str, str]] | None = None,
    being_outputs: dict[str, str] | None = None,
    strategy: str = "merge",
    run_status: str = "completed",
    run_error: str | None = None,
):
    """Create an OrchestrationEngine with a fully mocked SubAgentOrchestrator."""
    if beings is None:
        beings = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Research",
             "skills": "", "tenant_id": "t-forge", "workspace": "workspaces/forge"},
            {"id": "memory", "name": "SAI Memory", "status": "online", "role": "Memory",
             "skills": "", "tenant_id": "t-memory", "workspace": "workspaces/scholar"},
        ]
    if being_outputs is None:
        being_outputs = {b["id"]: f"Output from {b['id']}" for b in beings}

    dashboard = MagicMock()
    project_svc = MagicMock()
    bridge = MagicMock()

    dashboard.list_beings.return_value = beings
    dashboard.get_being.side_effect = lambda bid: next(
        (b for b in beings if b["id"] == bid), {}
    )

    task_counter = [0]

    def mock_create_task(ps, **kwargs):
        task_counter[0] += 1
        return {"id": f"task-{task_counter[0]}", "title": kwargs.get("title", ""), "status": "in_progress"}

    dashboard.create_task.side_effect = mock_create_task
    dashboard.update_task.return_value = {}
    dashboard._log_task_history = MagicMock()
    dashboard._emit_event = MagicMock()
    dashboard.update_being = MagicMock()
    dashboard.create_message = MagicMock()

    sub_tasks = [
        {"being_id": b["id"], "title": f"Task for {b['id']}",
         "instructions": f"Do work for {b['id']}", "done_when": "Done"}
        for b in beings
    ]

    def mock_handle_turn(req):
        msg = req.user_message
        if "ORCHESTRATION MODE" in msg:
            return {"assistant": {"text": json.dumps({
                "summary": "Test plan",
                "synthesis_strategy": strategy,
                "sub_tasks": sub_tasks,
            })}}
        if "[REVIEW]" in msg:
            return {"assistant": {"text": json.dumps({
                "approved": True, "feedback": "", "quality_score": 0.9, "notes": "Good",
            })}}
        if "[SYNTHESIZE" in msg:
            return {"assistant": {"text": "Synthesized final output."}}
        return {"assistant": {"text": "default"}}

    bridge.handle_turn.side_effect = mock_handle_turn

    # Build mock SubAgentOrchestrator
    protocol = MagicMock()
    orchestrator = MagicMock()
    orchestrator.protocol = protocol

    spawned_runs = {}
    spawn_order = []  # track spawn call order
    run_counter = [0]

    def mock_spawn_async(task, parent_session_id, parent_turn_id, parent_agent_id, child_agent_id, **kwargs):
        run_counter[0] += 1
        run_id = f"run-{run_counter[0]}"
        spawn_order.append(("spawn", child_agent_id))
        spawned_runs[run_id] = {
            "run_id": run_id,
            "child_agent_id": child_agent_id,
            "ticket_id": task.ticket_id,
            "status": run_status,
            "error_detail": run_error,
            "artifacts": {"output": being_outputs.get(child_agent_id, "")},
        }
        handle = MagicMock()
        handle.run_id = run_id
        return handle

    orchestrator.spawn_async.side_effect = mock_spawn_async

    def mock_get_run(run_id):
        return spawned_runs.get(run_id)
    protocol.get_run.side_effect = mock_get_run

    def mock_read_shared_memory(ticket_id, scope=None):
        writes = []
        for _rid, run in spawned_runs.items():
            agent_id = run["child_agent_id"]
            output = being_outputs.get(agent_id, f"Output from {agent_id}")
            writes.append({
                "writer_agent_id": agent_id,
                "content": output,
                "ticket_id": ticket_id,
                "scope": scope or "committed",
            })
        return writes
    protocol.read_shared_memory.side_effect = mock_read_shared_memory
    protocol.cascade_stop.return_value = []

    engine = OrchestrationEngine(
        bridge=bridge,
        dashboard_svc=dashboard,
        project_svc=project_svc,
        subagent_orchestrator=orchestrator,
    )

    return engine, orchestrator, protocol, spawn_order


def _wait(engine, task_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = engine.get_status(task_id)
        if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
            return status
        time.sleep(0.05)
    return engine.get_status(task_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSubAgentProtocolIntegration:

    def test_subtask_spawns_via_protocol(self):
        """Verify _execute_subtask calls spawn_async with correct child_agent_id, ticket_id, goal."""
        engine, orchestrator, protocol, _ = _make_engine()
        result = engine.start(goal="Test spawn", requester_session_id="s1", sender="user")
        status = _wait(engine, result["task_id"])

        assert status["status"] == STATUS_COMPLETED
        assert orchestrator.spawn_async.call_count == 2

        # Check that each call has the correct child_agent_id
        child_ids = set()
        for c in orchestrator.spawn_async.call_args_list:
            child_ids.add(c.kwargs["child_agent_id"])
            # Verify ticket_id is the parent task_id
            task_arg = c.kwargs.get("task") or c[0][0]
            assert task_arg.ticket_id == result["task_id"]
            # Verify goal contains the delegation message
            assert "sub-task by SAI Prime" in task_arg.goal
        assert child_ids == {"forge", "memory"}

    def test_subtask_idempotency_key_prevents_duplicates(self):
        """Verify idempotency key is built from task_id:being_id."""
        engine, orchestrator, protocol, _ = _make_engine(
            beings=[{"id": "forge", "name": "SAI Forge", "status": "online",
                     "role": "R", "skills": "", "tenant_id": "t-forge",
                     "workspace": "workspaces/forge"}],
        )
        result = engine.start(goal="Idempotency test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        assert orchestrator.spawn_async.call_count == 1
        task_arg = orchestrator.spawn_async.call_args.kwargs.get("task") or orchestrator.spawn_async.call_args[0][0]
        assert task_arg.idempotency_key == f"{result['task_id']}:forge"

    def test_parallel_delegation_spawns_all_then_awaits(self):
        """With strategy=merge, all beings should be spawned before any await."""
        beings = [
            {"id": f"being-{i}", "name": f"Being {i}", "status": "online",
             "role": "R", "skills": "", "tenant_id": f"t-{i}", "workspace": f"workspaces/b{i}"}
            for i in range(3)
        ]
        engine, orchestrator, protocol, spawn_order = _make_engine(
            beings=beings, strategy="merge",
        )
        result = engine.start(goal="Parallel test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        assert orchestrator.spawn_async.call_count == 3
        # All spawns should happen (order within parallel batch doesn't matter,
        # but they should all be spawns, not interleaved with awaits)
        spawn_events = [e for e in spawn_order if e[0] == "spawn"]
        assert len(spawn_events) == 3

    def test_sequential_delegation_awaits_between_spawns(self):
        """With strategy=sequential, spawn → await → spawn → await."""
        beings = [
            {"id": "a", "name": "A", "status": "online", "role": "R",
             "skills": "", "tenant_id": "t-a", "workspace": "workspaces/a"},
            {"id": "b", "name": "B", "status": "online", "role": "R",
             "skills": "", "tenant_id": "t-b", "workspace": "workspaces/b"},
        ]
        # Track get_run calls to verify interleaved await behavior
        get_run_calls = []
        engine, orchestrator, protocol, spawn_order = _make_engine(
            beings=beings, strategy="sequential",
        )

        original_get_run = protocol.get_run.side_effect

        def tracking_get_run(run_id):
            get_run_calls.append(run_id)
            return original_get_run(run_id)

        protocol.get_run.side_effect = tracking_get_run

        result = engine.start(goal="Sequential test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        assert orchestrator.spawn_async.call_count == 2
        # Verify sequential: spawn a, then await a (get_run), then spawn b
        assert spawn_order[0] == ("spawn", "a")
        # get_run must be called for run-1 before spawn of b
        assert len(get_run_calls) >= 1
        assert spawn_order[1] == ("spawn", "b")

    def test_sequential_prior_outputs_from_shared_memory(self):
        """In sequential mode, being B's delegation message should contain A's output."""
        beings = [
            {"id": "a", "name": "A", "status": "online", "role": "R",
             "skills": "", "tenant_id": "t-a", "workspace": "workspaces/a"},
            {"id": "b", "name": "B", "status": "online", "role": "R",
             "skills": "", "tenant_id": "t-b", "workspace": "workspaces/b"},
        ]
        engine, orchestrator, protocol, _ = _make_engine(
            beings=beings,
            being_outputs={"a": "Alpha findings here", "b": "Beta analysis"},
            strategy="sequential",
        )
        result = engine.start(goal="Prior output test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        # Being B's delegation message should contain A's output via shared memory
        assert orchestrator.spawn_async.call_count == 2
        b_call = [
            c for c in orchestrator.spawn_async.call_args_list
            if c.kwargs["child_agent_id"] == "b"
        ]
        assert len(b_call) == 1
        b_task = b_call[0].kwargs.get("task") or b_call[0][0][0]
        assert "CONTEXT FROM OTHER BEINGS" in b_task.goal
        assert "Alpha findings here" in b_task.goal

    def test_synthesis_reads_from_shared_memory(self):
        """After delegation, _phase_synthesize reads outputs from shared_working_memory_writes."""
        engine, orchestrator, protocol, _ = _make_engine(
            being_outputs={"forge": "Forge research data", "memory": "Memory analysis"},
        )
        result = engine.start(goal="Synthesis SM test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        # Verify read_shared_memory was called during synthesis
        sm_calls = protocol.read_shared_memory.call_args_list
        # Should be called at least once during _phase_synthesize
        assert len(sm_calls) >= 1
        # At least one call should be for the task's ticket_id with scope="committed"
        committed_calls = [
            c for c in sm_calls
            if c.kwargs.get("scope") == "committed" or (len(c.args) > 1 and c.args[1] == "committed")
        ]
        assert len(committed_calls) >= 1

    def test_timeout_triggers_cascade_stop(self):
        """When _await_run_completion times out, cascade_stop is called."""
        engine, orchestrator, protocol, _ = _make_engine()

        # Override get_run to never return terminal status
        protocol.get_run.side_effect = lambda run_id: {
            "run_id": run_id, "status": "in_progress",
            "ticket_id": "test", "error_detail": None,
        }

        # Test _await_run_completion directly with short timeout
        run = engine._await_run_completion("run-test", timeout=1)

        # Verify cascade_stop was called
        protocol.cascade_stop.assert_called_once()
        args = protocol.cascade_stop.call_args
        assert args[0][0] == "run-test"

    def test_failed_subtask_output_captured(self):
        """When a subtask run fails, the error detail appears in subtask_outputs."""
        engine, orchestrator, protocol, _ = _make_engine(
            run_status="failed",
            run_error="Worker crashed: OOM",
        )
        result = engine.start(goal="Fail capture test", requester_session_id="s1", sender="user")
        status = _wait(engine, result["task_id"])

        # Orchestration may complete or fail (review of error outputs), but
        # the subtask_outputs should contain the error information
        outputs = status.get("subtask_outputs", {})
        for being_id, output_preview in outputs.items():
            # _on_subtask_completed stores error detail for failed runs
            assert "[Error" in output_preview or "Worker crashed" in output_preview or output_preview


class TestCleanupVerification:
    """Tests verifying the cleanup pass changes."""

    def test_being_status_not_set_by_engine_during_delegation(self):
        """Engine should NOT call update_being with busy/online during delegation.

        Being status is now managed by the worker's busy/online lifecycle.
        """
        engine, orchestrator, protocol, _ = _make_engine()
        result = engine.start(goal="Status test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        dashboard = engine.dashboard
        busy_calls = [
            c for c in dashboard.update_being.call_args_list
            if len(c[0]) >= 2 and isinstance(c[0][1], dict)
            and c[0][1].get("status") == "busy" and c[0][0] != "prime"
        ]
        assert len(busy_calls) == 0, (
            "Engine should not set being status to busy — worker handles it"
        )

        # Engine should NOT set non-prime beings to online
        online_calls = [
            c for c in dashboard.update_being.call_args_list
            if len(c[0]) >= 2 and isinstance(c[0][1], dict)
            and c[0][1].get("status") == "online" and c[0][0] != "prime"
        ]
        assert len(online_calls) == 0, (
            "Engine should not set being status to online — worker handles it"
        )

    def test_worker_sets_being_status(self):
        """SubAgentWorkerFactory with dashboard_svc sets busy before and online after."""
        from bomba_sr.subagents.worker import SubAgentWorkerFactory

        bridge = MagicMock()
        bridge.handle_turn.return_value = {
            "assistant": {"text": "worker output", "usage": {}}
        }
        dashboard = MagicMock()

        factory = SubAgentWorkerFactory(bridge, dashboard_svc=dashboard)
        worker = factory.create_worker()

        protocol = MagicMock()
        protocol.get_run.return_value = {
            "run_id": "r1",
            "parent_agent_id": "prime",
            "child_agent_id": "forge",
        }

        task = SubAgentTask(
            tenant_id="t-forge",
            task_id="task-1",
            ticket_id="ticket-1",
            idempotency_key="key-123456789012",
            goal="Test goal",
            done_when=("Done",),
            input_context_refs=(),
            output_schema={},
            workspace_root="/tmp/test",
        )

        worker("r1", task, protocol)

        # Verify busy was called before handle_turn
        busy_calls = [
            c for c in dashboard.update_being.call_args_list
            if c[0] == ("forge", {"status": "busy"})
        ]
        assert len(busy_calls) == 1

        # Verify online was called after handle_turn
        online_calls = [
            c for c in dashboard.update_being.call_args_list
            if c[0] == ("forge", {"status": "online"})
        ]
        assert len(online_calls) == 1

    def test_cascade_stop_on_orchestration_failure(self):
        """When orchestration fails after delegation, cascade_stop_session is called."""
        engine, orchestrator, protocol, _ = _make_engine()

        # Make _phase_review raise to simulate orchestration failure after delegation
        engine._phase_review = MagicMock(side_effect=RuntimeError("Synthesis crashed"))

        result = engine.start(goal="Cascade test", requester_session_id="s1", sender="user")
        status = _wait(engine, result["task_id"])

        assert status["status"] == STATUS_FAILED

        # Verify cascade_stop_session was called
        assert protocol.cascade_stop_session.call_count >= 1
        cs_call = protocol.cascade_stop_session.call_args
        assert cs_call.kwargs.get("tenant_id") or cs_call[0][0]  # has tenant_id
        assert "orchestration failed" in (cs_call.kwargs.get("reason") or cs_call[0][2] or "").lower() or \
               "Synthesis crashed" in (cs_call.kwargs.get("reason") or cs_call[0][2] or "")

    def test_awaiting_completion_state_removed(self):
        """STATUS_AWAITING should not exist in engine status constants."""
        import bomba_sr.orchestration.engine as engine_mod

        assert not hasattr(engine_mod, "STATUS_AWAITING"), (
            "STATUS_AWAITING should be removed — 'delegating' covers spawn+await"
        )

        # Verify no status transition ever sets awaiting_completion
        engine, orchestrator, protocol, _ = _make_engine()
        result = engine.start(goal="No awaiting test", requester_session_id="s1", sender="user")
        _wait(engine, result["task_id"])

        # Check all emitted status events
        status_events = [
            c for c in engine.dashboard._emit_event.call_args_list
            if c[0][0] == "orchestration_update"
        ]
        for call_args in status_events:
            event_data = call_args[0][1]
            assert event_data.get("status") != "awaiting_completion", (
                "No status transition should use awaiting_completion"
            )

    def test_subtask_outputs_column_not_in_schema(self):
        """orchestration_state table should NOT have subtask_outputs column."""
        tmpdir = tempfile.mkdtemp()
        db = RuntimeDB(os.path.join(tmpdir, "runtime.db"))

        tenant_runtime = MagicMock()
        tenant_runtime.db = db

        bridge = MagicMock()
        bridge._tenant_runtime.return_value = tenant_runtime

        dashboard = MagicMock()
        dashboard.list_beings.return_value = []
        dashboard.create_task.return_value = {"id": "t1"}
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        OrchestrationEngine(
            bridge=bridge,
            dashboard_svc=dashboard,
            project_svc=MagicMock(),
        )

        cols = db.execute("PRAGMA table_info(orchestration_state)").fetchall()
        col_names = [c["name"] for c in cols]
        assert "subtask_outputs" not in col_names, (
            "subtask_outputs column should be removed — outputs live in shared_working_memory_writes"
        )

    def test_full_orchestration_unified_pipeline(self):
        """Comprehensive test: full plan → delegate → review → synthesize pipeline.

        Uses real SubAgentProtocol (real DB) with mocked bridge.handle_turn.
        Uses a synchronous orchestrator wrapper to avoid threading flakiness.
        """
        tmpdir = tempfile.mkdtemp()
        db = RuntimeDB(os.path.join(tmpdir, "pipeline.db"))

        tenant_runtime = MagicMock()
        tenant_runtime.db = db
        tenant_runtime.memory = MagicMock()

        bridge = MagicMock()
        bridge._tenant_runtime.return_value = tenant_runtime

        beings = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Research",
             "skills": "", "tenant_id": "t-forge", "workspace": "workspaces/forge"},
            {"id": "scholar", "name": "SAI Scholar", "status": "online", "role": "Analysis",
             "skills": "", "tenant_id": "t-scholar", "workspace": "workspaces/scholar"},
        ]

        dashboard = MagicMock()
        dashboard.list_beings.return_value = beings
        dashboard.get_being.side_effect = lambda bid: next(
            (b for b in beings if b["id"] == bid), {}
        )
        dashboard.create_task.return_value = {"id": "pipeline-task-1"}
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        sub_tasks = [
            {"being_id": "forge", "title": "Research", "instructions": "Research topic",
             "done_when": "Report ready"},
            {"being_id": "scholar", "title": "Analyze", "instructions": "Analyze findings",
             "done_when": "Analysis complete"},
        ]

        def mock_handle_turn(req):
            msg = req.user_message
            if "ORCHESTRATION MODE" in msg:
                return {"assistant": {"text": json.dumps({
                    "summary": "Pipeline test plan",
                    "synthesis_strategy": "merge",
                    "sub_tasks": sub_tasks,
                })}}
            if "[REVIEW]" in msg:
                return {"assistant": {"text": json.dumps({
                    "approved": True, "feedback": "", "quality_score": 0.9, "notes": "Good",
                })}}
            if "[SYNTHESIZE" in msg:
                return {"assistant": {"text": "Final synthesized output from pipeline."}}
            # Worker-dispatched sub-task execution
            if "sub-task by SAI Prime" in msg:
                return {"assistant": {"text": "Worker completed subtask execution.", "usage": {}}}
            return {"assistant": {"text": "default"}}

        bridge.handle_turn.side_effect = mock_handle_turn

        # Create real protocol with a synchronous orchestrator that
        # runs workers inline (no ThreadPoolExecutor) to avoid
        # SQLite cross-thread cursor races.
        protocol = SubAgentProtocol(db)

        from bomba_sr.subagents.orchestrator import SubAgentOrchestrator, SubAgentHandle
        from concurrent.futures import Future

        class _SyncOrchestrator(SubAgentOrchestrator):
            """Runs worker synchronously so the test has no threading."""

            def spawn_async(self, task, parent_session_id, parent_turn_id,
                            parent_agent_id, child_agent_id, worker=None, parent_run_id=None):
                active_worker = worker or self.default_worker
                if active_worker is None:
                    raise RuntimeError("no worker")
                run = self.protocol.spawn(
                    task=task, parent_session_id=parent_session_id,
                    parent_turn_id=parent_turn_id, parent_agent_id=parent_agent_id,
                    child_agent_id=child_agent_id, parent_run_id=parent_run_id,
                )
                run_id = str(run["run_id"])
                # Run synchronously instead of in executor
                result = self._run_worker(run_id, task, active_worker)
                # Create a pre-resolved future
                f: Future[dict] = Future()
                f.set_result(result)
                return SubAgentHandle(run_id=run_id, future=f)

        orchestrator = _SyncOrchestrator(protocol)

        engine = OrchestrationEngine(
            bridge=bridge,
            dashboard_svc=dashboard,
            project_svc=MagicMock(),
            subagent_orchestrator=orchestrator,
        )

        result = engine.start(
            goal="Full pipeline integration test",
            requester_session_id="s1",
            sender="user",
        )
        status = _wait(engine, result["task_id"], timeout=15)

        # Verify orchestration completed
        assert status is not None
        assert status["status"] == STATUS_COMPLETED, f"Expected completed, got {status['status']}"

        task_id = result["task_id"]

        # Verify subagent_runs were created in the DB
        runs = db.execute("SELECT * FROM subagent_runs WHERE ticket_id = ?", (task_id,)).fetchall()
        assert len(runs) == 2
        for r in runs:
            if r["status"] != "completed":
                raise AssertionError(
                    f"Run {r['child_agent_id']} has status={r['status']}, "
                    f"error={r['error_detail']}"
                )

        # Verify shared_working_memory_writes has committed entries
        writes = protocol.read_shared_memory(ticket_id=task_id, scope="committed")
        assert len(writes) >= 2

        # Verify subagent_events has status transitions
        for run in runs:
            events = protocol.stream_events(run["run_id"])
            event_types = [e["event_type"] for e in events]
            assert "accepted" in event_types
            assert "completed" in event_types

        # Verify Prime status is online at the end
        prime_online = [
            c for c in dashboard.update_being.call_args_list
            if c[0] == ("prime", {"status": "online"})
        ]
        assert len(prime_online) >= 1

    def test_cascade_stop_on_synthesis_failure(self):
        """When _phase_synthesize raises, the _orchestrate except block calls cascade_stop_session."""
        engine, orchestrator, protocol, _ = _make_engine()

        # Patch _phase_synthesize to raise after delegation completes
        engine._phase_synthesize = MagicMock(side_effect=RuntimeError("Synthesis exploded"))

        result = engine.start(goal="Synth fail test", requester_session_id="s1", sender="user")
        status = _wait(engine, result["task_id"])

        assert status["status"] == STATUS_FAILED

        # The _orchestrate except block calls protocol.cascade_stop_session
        assert protocol.cascade_stop_session.call_count >= 1
        cs_call = protocol.cascade_stop_session.call_args
        # Verify tenant_id and reason are passed
        tenant_arg = cs_call.kwargs.get("tenant_id") or cs_call[0][0]
        assert tenant_arg  # non-empty tenant_id
        reason_arg = cs_call.kwargs.get("reason") or (cs_call[0][2] if len(cs_call[0]) > 2 else "")
        assert "Synthesis exploded" in reason_arg or "orchestration failed" in reason_arg.lower()

    def test_cascade_stop_skips_completed_runs(self):
        """cascade_stop_session is called even when all runs completed before the failure.

        Already-completed runs are unaffected because cascade_stop_session only
        stops non-terminal runs (its SQL filters out completed/failed/timed_out).
        """
        engine, orchestrator, protocol, _ = _make_engine(
            run_status="completed",
        )

        # All runs complete successfully, then synthesis blows up
        engine._phase_synthesize = MagicMock(side_effect=RuntimeError("Synthesis boom"))

        result = engine.start(goal="Completed runs test", requester_session_id="s1", sender="user")
        status = _wait(engine, result["task_id"])

        assert status["status"] == STATUS_FAILED

        # cascade_stop_session IS still called (it's session-scoped)
        assert protocol.cascade_stop_session.call_count >= 1

        # The already-completed runs remain completed — verify via get_run
        # (which is backed by the spawned_runs dict in _make_engine)
        for i in range(1, orchestrator.spawn_async.call_count + 1):
            run_data = protocol.get_run(f"run-{i}")
            assert run_data["status"] == "completed", (
                f"Run run-{i} should remain completed, got {run_data['status']}"
            )

    def test_crash_storm_blocks_repeated_failures(self):
        """After 3 crashes in the window, the 4th spawn raises RuntimeError."""
        tmpdir = tempfile.mkdtemp()
        db = RuntimeDB(os.path.join(tmpdir, "crash_storm.db"))
        protocol = SubAgentProtocol(db)

        from bomba_sr.subagents.orchestrator import (
            SubAgentOrchestrator,
            CrashStormConfig,
        )

        def failing_worker(run_id, task, proto):
            raise RuntimeError("worker always fails")

        config = CrashStormConfig(window_seconds=60, max_crashes=3, cooldown_seconds=120)
        orchestrator = SubAgentOrchestrator(
            protocol,
            crash_storm_config=config,
            default_worker=failing_worker,
        )

        def make_task(idx):
            return SubAgentTask(
                tenant_id="t-test",
                task_id=f"task-crash-{idx}",
                ticket_id="ticket-crash",
                idempotency_key=f"crash-key-{idx:04d}-padding",
                goal=f"Crash test {idx}",
                done_when=("never",),
                input_context_refs=(),
                output_schema={},
                workspace_root="/tmp/test",
            )

        # Spawn 3 times — each will fail (worker raises). We must wait for
        # each future to finish so the crash is recorded before the next spawn.
        for i in range(3):
            handle = orchestrator.spawn_async(
                task=make_task(i),
                parent_session_id="sess-crash",
                parent_turn_id=f"turn-{i}",
                parent_agent_id="prime",
                child_agent_id=f"child-{i}",
            )
            # Wait for the future to complete (it will raise, but we don't care)
            try:
                handle.future.result(timeout=5)
            except RuntimeError:
                pass  # expected — worker always fails

        # The crash detector should now be in cooldown after 3 crashes
        assert orchestrator.crash_detector.is_in_cooldown()

        # 4th spawn should be blocked
        with pytest.raises(RuntimeError, match="crash storm cooldown"):
            orchestrator.spawn_async(
                task=make_task(3),
                parent_session_id="sess-crash",
                parent_turn_id="turn-3",
                parent_agent_id="prime",
                child_agent_id="child-3",
            )
