"""Tests for orchestration resume notification and failure handling."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.orchestration.engine import (
    OrchestrationEngine,
    OrchestrationPlan,
    SubTaskPlan,
    STATUS_DELEGATING,
    STATUS_FAILED,
    orchestration_session_id,
)
from bomba_sr.storage.db import RuntimeDB


# ---------------------------------------------------------------------------
# Helper: create a minimal engine backed by a real SQLite DB
# ---------------------------------------------------------------------------

def _make_engine(
    db: RuntimeDB | None = None,
    tmpdir: str | None = None,
):
    """Build an OrchestrationEngine backed by a real RuntimeDB.

    Returns (engine, db, tmpdir) so callers can inspect the database and
    create new engine instances pointing at the same DB file.
    """
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
        bridge=bridge,
        dashboard_svc=dashboard,
        project_svc=project_svc,
    )
    return engine, db, tmpdir


def _make_plan_json(sub_tasks: list[SubTaskPlan], strategy: str = "parallel") -> str:
    """Serialize an OrchestrationPlan to JSON suitable for DB insertion."""
    plan = OrchestrationPlan(
        summary="Test plan",
        sub_tasks=sub_tasks,
        synthesis_strategy=strategy,
    )
    return json.dumps(plan.to_dict())


def _insert_orchestration_state(
    db: RuntimeDB,
    task_id: str,
    status: str,
    goal: str = "Test goal",
    sender: str = "user",
    plan_json: str | None = None,
    subtask_ids: dict[str, str] | None = None,
) -> None:
    """Insert a row into orchestration_state with the given fields."""
    now = datetime.now(timezone.utc).isoformat()
    db.execute_commit(
        """
        INSERT INTO orchestration_state
            (task_id, goal, orch_session_id, requester_session,
             sender, status, plan_json, subtask_ids,
             subtask_reviews, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            goal,
            f"orchestration:{task_id}",
            "mc-chat-prime",
            sender,
            status,
            plan_json,
            json.dumps(subtask_ids or {}),
            json.dumps({}),
            now,
            now,
        ),
    )


# ---------------------------------------------------------------------------
# Test 9: User notification on resume
# ---------------------------------------------------------------------------

class TestResumeNotification:
    """Verify that resume_orchestration sends a notification to the original requester."""

    def test_user_notified_on_resume(self):
        """When an orchestration is resumed after a server restart, the user
        who requested the task receives a direct message indicating that the
        system restarted and their task is being resumed."""
        engine, db, tmpdir = _make_engine()

        sub_tasks = [SubTaskPlan("forge", "Build UI", "Create the dashboard UI", "UI renders")]
        plan_json = _make_plan_json(sub_tasks)
        task_id = "task-resume-notify-1"

        _insert_orchestration_state(
            db,
            task_id,
            status=STATUS_DELEGATING,
            goal="Build the dashboard",
            sender="alice",
            plan_json=plan_json,
            subtask_ids={"forge": "run-1"},
        )

        # Patch _resume_from_status to a no-op so no actual pipeline logic runs
        with patch.object(engine, "_resume_from_status"):
            # Also patch threading.Thread so no daemon thread is spawned
            with patch("bomba_sr.orchestration.engine.threading.Thread") as mock_thread:
                engine.resume_orchestration(task_id)

        # The notification should have been sent before the thread spawn
        engine.dashboard.create_message.assert_called_once()
        call_kwargs = engine.dashboard.create_message.call_args
        _, kwargs = call_kwargs

        assert kwargs["sender"] == "prime"
        assert "System restarted" in kwargs["content"]
        assert "Build the dashboard" in kwargs["content"]
        assert kwargs["targets"] == ["alice"]
        assert kwargs["msg_type"] == "direct"
        assert kwargs["task_ref"] == task_id


# ---------------------------------------------------------------------------
# Test 10: Resume failure marks orchestration as failed
# ---------------------------------------------------------------------------

class TestResumeFailure:
    """Verify that exceptions during resume mark the orchestration as failed
    and trigger proper cleanup."""

    def test_resume_failure_marks_orchestration_failed(self):
        """When _resume_from_status encounters an exception during delegation
        resume, it should:
        1. Mark the orchestration status as STATUS_FAILED in the DB
        2. Call protocol.cascade_stop_session with the orch session and error reason
        3. Call dashboard.update_task with status='failed'
        4. Always call dashboard.update_being('prime', {'status': 'online'}) in the finally block
        """
        protocol = MagicMock()
        engine, db, tmpdir = _make_engine()
        engine.protocol = protocol

        sub_tasks = [SubTaskPlan("forge", "Build API", "Create REST endpoints", "Endpoints work")]
        plan_json = _make_plan_json(sub_tasks)
        task_id = "task-resume-fail-1"

        _insert_orchestration_state(
            db,
            task_id,
            status=STATUS_DELEGATING,
            goal="Build the API",
            sender="bob",
            plan_json=plan_json,
            subtask_ids={"forge": "run-1"},
        )

        # Load state and populate the in-memory cache
        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        # Patch _resume_delegation to raise an error
        with patch.object(
            engine, "_resume_delegation",
            side_effect=RuntimeError("something broke"),
        ):
            engine._resume_from_status(task_id, state)

        # 1. Verify the orchestration status is now STATUS_FAILED in the DB
        row = db.execute(
            "SELECT status FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        assert row["status"] == STATUS_FAILED

        # 2. Verify protocol.cascade_stop_session was called with orch session and reason
        orch_session = orchestration_session_id(task_id)
        protocol.cascade_stop_session.assert_called_once()
        cascade_kwargs = protocol.cascade_stop_session.call_args
        _, kwargs = cascade_kwargs
        assert kwargs["session_id"] == orch_session
        assert "something broke" in kwargs["reason"]

        # 3. Verify dashboard.update_task was called with status="failed"
        engine.dashboard.update_task.assert_called_once_with(
            engine.project_svc, task_id, status="failed",
        )

        # 4. Verify dashboard.update_being was called with prime status online (finally block)
        engine.dashboard.update_being.assert_called_with("prime", {"status": "online"})
