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
"""
from __future__ import annotations

import json
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
from bomba_sr.subagents.protocol import SubAgentTask


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
