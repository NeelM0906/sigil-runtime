"""Tests for orchestration resume from various persisted states.

Covers:
  - Resume from delegating with partial subtask completion
  - Resume from reviewing (reloads outputs, runs review + synthesize)
  - Resume from synthesizing (reloads outputs, runs only synthesize)
  - Resume from planning (full pipeline restart)
"""
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
    STATUS_PLANNING,
    STATUS_DELEGATING,
    STATUS_REVIEWING,
    STATUS_REVISING,
    STATUS_SYNTHESIZING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from bomba_sr.storage.db import RuntimeDB


# ---------------------------------------------------------------------------
# Helper: create a minimal engine backed by a real SQLite DB
# ---------------------------------------------------------------------------

def _make_engine(
    db: RuntimeDB | None = None,
    tmpdir: str | None = None,
    protocol: Any | None = None,
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
    # Make bridge.handle_turn return a valid result for _phase_plan, _phase_review, _phase_synthesize
    bridge.handle_turn.return_value = {
        "assistant": {
            "text": json.dumps({
                "summary": "Test plan",
                "sub_tasks": [
                    {"being_id": "forge", "title": "Task A", "instructions": "Do A", "done_when": "A done"},
                ],
                "synthesis_strategy": "parallel",
            })
        }
    }

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

    # If protocol is provided, wire it in after construction
    if protocol is not None:
        engine.protocol = protocol

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
            f"Goal for {task_id}",
            f"orchestration:{task_id}",
            "mc-chat-prime",
            "user",
            status,
            plan_json,
            json.dumps(subtask_ids or {}),
            json.dumps({}),
            now,
            now,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResumeFromStates:
    """Verify _resume_from_status re-enters the pipeline at the correct phase."""

    def test_resume_from_delegating_with_partial_completion(self):
        """When resuming from 'delegating', completed subtasks are skipped,
        failed/interrupted ones are re-spawned, and outputs are reloaded from
        shared memory before continuing to review + synthesize."""
        protocol = MagicMock()

        # protocol.get_run returns completed for forge, failed for scholar
        def _get_run(run_id: str) -> dict[str, Any]:
            if run_id == "run-1":
                return {"status": "completed"}
            elif run_id == "run-2":
                return {"status": "failed"}
            return {"status": "unknown"}

        protocol.get_run.side_effect = _get_run
        protocol.read_shared_memory.return_value = [
            {
                "writer_agent_id": "forge",
                "content": "Forge output data",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        engine, db, tmpdir = _make_engine(protocol=protocol)

        sub_tasks = [
            SubTaskPlan("forge", "Task A", "Do A", "A done"),
            SubTaskPlan("scholar", "Task B", "Do B", "B done"),
        ]
        plan_json = _make_plan_json(sub_tasks)

        task_id = "task-resume-deleg-1"
        _insert_orchestration_state(
            db, task_id,
            status=STATUS_DELEGATING,
            plan_json=plan_json,
            subtask_ids={"forge": "run-1", "scholar": "run-2"},
        )

        # Load state into engine in-memory cache (as resume_orchestration would)
        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        # Patch _execute_subtask to return a new run_id for the re-spawned scholar
        with (
            patch.object(engine, "_execute_subtask", return_value="run-3") as mock_exec,
            patch.object(engine, "_await_run_completion", return_value={"status": "completed"}) as mock_await,
            patch.object(engine, "_on_subtask_completed") as mock_on_complete,
            patch.object(engine, "_update_post_delegation") as mock_post_deleg,
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
        ):
            engine._resume_from_status(task_id, state)

            # _execute_subtask should be called once -- only for scholar (forge was completed)
            assert mock_exec.call_count == 1
            executed_sub = mock_exec.call_args[0][1]  # second positional arg is SubTaskPlan
            assert executed_sub.being_id == "scholar"

            # protocol.get_run should have been called for both run-1 and run-2
            get_run_calls = [c[0][0] for c in protocol.get_run.call_args_list]
            assert "run-1" in get_run_calls
            assert "run-2" in get_run_calls

            # Shared memory was read and forge's output was loaded
            with engine._lock:
                outputs = engine._active[task_id]["subtask_outputs"]
            assert "forge" in outputs
            assert outputs["forge"] == "Forge output data"

            # Pipeline continued through post-delegation, review, and synthesize
            mock_post_deleg.assert_called_once_with(task_id)
            mock_review.assert_called_once_with(task_id)
            mock_synth.assert_called_once_with(task_id)

    def test_resume_from_reviewing(self):
        """When resuming from 'reviewing', outputs are reloaded from shared
        memory, then review and synthesize phases run."""
        protocol = MagicMock()
        protocol.read_shared_memory.return_value = [
            {
                "writer_agent_id": "forge",
                "content": "Forge review output",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        engine, db, tmpdir = _make_engine(protocol=protocol)

        sub_tasks = [SubTaskPlan("forge", "Task A", "Do A", "A done")]
        plan_json = _make_plan_json(sub_tasks)

        task_id = "task-resume-review-1"
        _insert_orchestration_state(
            db, task_id,
            status=STATUS_REVIEWING,
            plan_json=plan_json,
            subtask_ids={"forge": "run-1"},
        )

        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        with (
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
        ):
            engine._resume_from_status(task_id, state)

            # Outputs should be reloaded from shared memory
            protocol.read_shared_memory.assert_called_once_with(
                ticket_id=task_id, scope="committed",
            )
            with engine._lock:
                outputs = engine._active[task_id]["subtask_outputs"]
            assert "forge" in outputs
            assert outputs["forge"] == "Forge review output"

            # Review and synthesize both called
            mock_review.assert_called_once_with(task_id)
            mock_synth.assert_called_once_with(task_id)

    def test_resume_from_synthesizing(self):
        """When resuming from 'synthesizing', outputs are reloaded from shared
        memory, then only the synthesize phase runs (review is skipped)."""
        protocol = MagicMock()
        protocol.read_shared_memory.return_value = [
            {
                "writer_agent_id": "forge",
                "content": "Forge synth output",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "writer_agent_id": "scholar",
                "content": "Scholar synth output",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        engine, db, tmpdir = _make_engine(protocol=protocol)

        sub_tasks = [
            SubTaskPlan("forge", "Task A", "Do A", "A done"),
            SubTaskPlan("scholar", "Task B", "Do B", "B done"),
        ]
        plan_json = _make_plan_json(sub_tasks)

        task_id = "task-resume-synth-1"
        _insert_orchestration_state(
            db, task_id,
            status=STATUS_SYNTHESIZING,
            plan_json=plan_json,
            subtask_ids={"forge": "run-1", "scholar": "run-2"},
        )

        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        with (
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
        ):
            engine._resume_from_status(task_id, state)

            # _phase_review must NOT be called for synthesizing status
            mock_review.assert_not_called()

            # _phase_synthesize must be called
            mock_synth.assert_called_once_with(task_id)

            # Outputs should be loaded from shared memory
            with engine._lock:
                outputs = engine._active[task_id]["subtask_outputs"]
            assert "forge" in outputs
            assert outputs["forge"] == "Forge synth output"
            assert "scholar" in outputs
            assert outputs["scholar"] == "Scholar synth output"

    def test_resume_from_planning(self):
        """When resuming from 'planning' (plan never completed), the full
        pipeline restarts: plan -> delegate -> post-delegation -> review -> synthesize."""
        engine, db, tmpdir = _make_engine()

        task_id = "task-resume-plan-1"
        _insert_orchestration_state(
            db, task_id,
            status=STATUS_PLANNING,
            plan_json=None,  # No plan persisted yet
            subtask_ids={},
        )

        state = engine._db_load_state(task_id)
        assert state is not None
        with engine._lock:
            engine._active[task_id] = state

        with (
            patch.object(engine, "_phase_plan") as mock_plan,
            patch.object(engine, "_phase_delegate") as mock_delegate,
            patch.object(engine, "_update_post_delegation") as mock_post_deleg,
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synth,
        ):
            engine._resume_from_status(task_id, state)

            # Full pipeline should execute in order
            mock_plan.assert_called_once_with(task_id)
            mock_delegate.assert_called_once_with(task_id)
            mock_post_deleg.assert_called_once_with(task_id)
            mock_review.assert_called_once_with(task_id)
            mock_synth.assert_called_once_with(task_id)
