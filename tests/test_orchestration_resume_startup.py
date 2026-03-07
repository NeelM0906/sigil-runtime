"""Tests for orchestration resume behavior on server startup.

Verifies:
  - Stale orchestrations (>24h) are marked failed without resume attempt
  - Recent orchestrations (<=24h) trigger resume_orchestration
  - Sequential resume collects prior outputs from shared memory
  - Interrupted runs are marked failed before re-spawning
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.orchestration.engine import (
    OrchestrationEngine,
    OrchestrationPlan,
    SubTaskPlan,
    STATUS_PLANNING,
    STATUS_DELEGATING,
    STATUS_REVIEWING,
    STATUS_SYNTHESIZING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)


def _make_engine(db=None, tmpdir=None):
    """Build an OrchestrationEngine with a real RuntimeDB and mocked services."""
    if tmpdir is None:
        tmpdir = tempfile.mkdtemp()
    if db is None:
        db = RuntimeDB(os.path.join(tmpdir, "runtime.db"))

    tenant_runtime = MagicMock()
    tenant_runtime.db = db

    bridge = MagicMock()
    bridge._tenant_runtime.return_value = tenant_runtime
    bridge.handle_turn.return_value = {"assistant": {"text": "{}"}}

    dashboard = MagicMock()
    dashboard.list_beings.return_value = []
    dashboard.create_task.return_value = {"id": "task-1"}
    dashboard.update_task.return_value = {}
    dashboard._log_task_history = MagicMock()
    dashboard._emit_event = MagicMock()
    dashboard.update_being = MagicMock()
    dashboard.create_message = MagicMock()

    project_svc = MagicMock()

    engine = OrchestrationEngine(
        bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
    )
    return engine, db, tmpdir


def _insert_orchestration_row(
    db: RuntimeDB,
    task_id: str,
    status: str,
    updated_at: str,
    goal: str = "test goal",
    plan_json: str | None = None,
    subtask_ids: str = "{}",
    subtask_reviews: str = "{}",
    created_at: str | None = None,
) -> None:
    """Insert a row directly into orchestration_state for testing."""
    if created_at is None:
        created_at = updated_at
    orch_session = f"orchestration:{task_id}"
    db.execute_commit(
        """
        INSERT INTO orchestration_state
            (task_id, goal, orch_session_id, requester_session,
             sender, status, plan_json, subtask_ids,
             subtask_reviews, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, goal, orch_session, "req-session-1",
            "user", status, plan_json, subtask_ids,
            subtask_reviews, created_at, updated_at,
        ),
    )


# ---------------------------------------------------------------------------
# Startup recovery tests: stale vs recent orchestrations
# ---------------------------------------------------------------------------

class TestStartupRecovery:
    """Verify cleanup_orphaned_orchestrations routes stale vs recent correctly."""

    def test_stale_orchestration_not_resumed(self):
        """Orchestrations older than 24h are marked failed, not resumed."""
        engine, db, tmpdir = _make_engine()

        # Insert a delegating orchestration last updated 25 hours ago
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        task_id = "task-stale-001"
        _insert_orchestration_row(db, task_id, STATUS_DELEGATING, stale_time)

        # Patch resume_orchestration to verify it is NOT called
        with patch.object(engine, "resume_orchestration") as mock_resume:
            processed = engine.cleanup_orphaned_orchestrations()

        assert processed == 1
        mock_resume.assert_not_called()

        # Verify the row is now STATUS_FAILED in the database
        row = db.execute(
            "SELECT status FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        assert row is not None
        assert row["status"] == STATUS_FAILED

    def test_recent_orchestration_resumed(self):
        """Orchestrations within 24h trigger resume_orchestration."""
        engine, db, tmpdir = _make_engine()

        # Insert a delegating orchestration last updated 1 hour ago with a valid plan
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        task_id = "task-recent-001"
        plan_json = json.dumps({
            "summary": "Test plan",
            "sub_tasks": [
                {
                    "being_id": "forge",
                    "title": "Forge sub-task",
                    "instructions": "Do the thing",
                    "done_when": "Thing is done",
                },
            ],
            "synthesis_strategy": "parallel",
        })
        _insert_orchestration_row(
            db, task_id, STATUS_DELEGATING, recent_time, plan_json=plan_json,
        )

        # Patch resume_orchestration to prevent spawning a real daemon thread
        with patch.object(engine, "resume_orchestration") as mock_resume:
            processed = engine.cleanup_orphaned_orchestrations()

        assert processed == 1
        mock_resume.assert_called_once_with(task_id)


# ---------------------------------------------------------------------------
# Resume delegation tests: sequential + interrupted run handling
# ---------------------------------------------------------------------------

class TestResumeDelegation:
    """Verify _resume_delegation handles sequential and interrupted runs."""

    def test_sequential_resume_preserves_prior_outputs(self):
        """For sequential strategy, completed subtasks are skipped and their
        outputs are collected from shared memory for injection into later subtasks."""
        engine, db, tmpdir = _make_engine()

        task_id = "task-seq-001"
        plan_json = json.dumps({
            "summary": "Sequential test plan",
            "sub_tasks": [
                {"being_id": "forge", "title": "Forge work", "instructions": "Build it", "done_when": "Built"},
                {"being_id": "scholar", "title": "Scholar research", "instructions": "Research it", "done_when": "Researched"},
                {"being_id": "herald", "title": "Herald announce", "instructions": "Announce it", "done_when": "Announced"},
            ],
            "synthesis_strategy": "sequential",
        })
        subtask_ids = json.dumps({
            "forge": "run-1",
            "scholar": "run-2",
            "herald": "run-3",
        })
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _insert_orchestration_row(
            db, task_id, STATUS_DELEGATING, recent_time,
            plan_json=plan_json, subtask_ids=subtask_ids,
        )

        # Set up a mock protocol
        protocol = MagicMock()
        engine.protocol = protocol
        engine.subagent_orch = MagicMock()

        # forge completed, scholar completed, herald failed
        def mock_get_run(run_id):
            runs = {
                "run-1": {"status": "completed"},
                "run-2": {"status": "completed"},
                "run-3": {"status": "failed"},
            }
            return runs.get(run_id)

        protocol.get_run.side_effect = mock_get_run

        # Shared memory returns forge and scholar outputs
        protocol.read_shared_memory.return_value = [
            {"writer_agent_id": "forge", "content": "Forge output data", "ticket_id": task_id, "scope": "committed"},
            {"writer_agent_id": "scholar", "content": "Scholar output data", "ticket_id": task_id, "scope": "committed"},
        ]

        # Load state into _active cache (mimic what resume_orchestration does)
        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        # Patch downstream methods to isolate _resume_delegation behavior
        with (
            patch.object(engine, "_execute_subtask", return_value="run-new-herald") as mock_execute,
            patch.object(engine, "_await_run_completion", return_value={"status": "completed"}) as mock_await,
            patch.object(engine, "_on_subtask_completed") as mock_on_completed,
            patch.object(engine, "_update_post_delegation") as mock_post_deleg,
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
            patch.object(engine, "_collect_prior_outputs_from_shared_memory", return_value={"forge": "Forge output data", "scholar": "Scholar output data"}) as mock_collect_prior,
        ):
            engine._resume_from_status(task_id, state)

        # Only herald should have been re-spawned (forge and scholar completed)
        assert mock_execute.call_count == 1
        execute_call_args = mock_execute.call_args
        # The second positional arg is the SubTaskPlan
        spawned_sub = execute_call_args[0][1]
        assert spawned_sub.being_id == "herald"

        # _collect_prior_outputs_from_shared_memory was called because strategy is sequential
        mock_collect_prior.assert_called_once()
        collect_call_args = mock_collect_prior.call_args[0]
        assert collect_call_args[0] == task_id  # task_id
        assert collect_call_args[2] == "herald"  # current_being_id

        # Prior outputs were passed into _execute_subtask as prior_outputs kwarg
        assert execute_call_args[1].get("prior_outputs") == {
            "forge": "Forge output data",
            "scholar": "Scholar output data",
        }

    def test_resume_interrupted_run_marked_failed_first(self):
        """Runs that were active (accepted/running) at crash time are failed
        before being re-spawned. The fail call must precede the re-spawn."""
        engine, db, tmpdir = _make_engine()

        task_id = "task-interrupt-001"
        plan_json = json.dumps({
            "summary": "Interrupted run test",
            "sub_tasks": [
                {"being_id": "forge", "title": "Forge work", "instructions": "Build it", "done_when": "Built"},
            ],
            "synthesis_strategy": "parallel",
        })
        subtask_ids = json.dumps({"forge": "run-1"})
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _insert_orchestration_row(
            db, task_id, STATUS_DELEGATING, recent_time,
            plan_json=plan_json, subtask_ids=subtask_ids,
        )

        # Set up a mock protocol
        protocol = MagicMock()
        engine.protocol = protocol
        engine.subagent_orch = MagicMock()

        # Run was "accepted" (in-flight) when the server died
        protocol.get_run.return_value = {"status": "accepted"}
        protocol.read_shared_memory.return_value = []

        # Load state into _active cache
        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        # Track the order of calls: protocol.fail MUST happen before _execute_subtask
        call_order = []

        def track_fail(*args, **kwargs):
            call_order.append("fail")

        protocol.fail.side_effect = track_fail

        def track_execute(*args, **kwargs):
            call_order.append("execute_subtask")
            return "run-new-1"

        with (
            patch.object(engine, "_execute_subtask", side_effect=track_execute) as mock_execute,
            patch.object(engine, "_await_run_completion", return_value={"status": "completed"}) as mock_await,
            patch.object(engine, "_on_subtask_completed") as mock_on_completed,
            patch.object(engine, "_update_post_delegation") as mock_post_deleg,
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
        ):
            engine._resume_from_status(task_id, state)

        # protocol.fail was called with run-1 and reason mentioning server restart
        protocol.fail.assert_called_once()
        fail_args, fail_kwargs = protocol.fail.call_args
        if fail_args:
            assert fail_args[0] == "run-1"
        else:
            assert fail_kwargs.get("run_id") == "run-1"
        # Check reason contains "Server restart"
        reason = fail_kwargs.get("reason", "") or (fail_args[1] if len(fail_args) > 1 else "")
        assert "Server restart" in reason

        # _execute_subtask was called to re-spawn the subtask
        mock_execute.assert_called_once()
        spawned_sub = mock_execute.call_args[0][1]
        assert spawned_sub.being_id == "forge"

        # The fail call happened BEFORE the re-spawn
        assert call_order.index("fail") < call_order.index("execute_subtask"), (
            f"Expected fail before execute_subtask, but got: {call_order}"
        )
