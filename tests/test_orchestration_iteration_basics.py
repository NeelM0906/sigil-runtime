"""Tests for multi-round iteration basics: max_rounds, early stop."""
from __future__ import annotations

import os
import tempfile
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

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


def _setup_active_state(engine, task_id, plan):
    """Insert an orchestration state with the given plan into the engine's _active cache."""
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "task_id": task_id,
        "goal": "Test goal",
        "orchestration_session": f"orchestration:{task_id}",
        "requester_session": "s1",
        "sender": "user",
        "status": STATUS_PLANNING,
        "plan": plan,
        "subtask_ids": {},
        "subtask_outputs": {},
        "subtask_reviews": {},
        "created_at": now,
    }
    with engine._lock:
        engine._active[task_id] = state


class TestIterationBasics:
    """Tests for OrchestrationPlan.max_rounds and multi-round iteration logic."""

    def test_max_rounds_default_1_no_iteration(self):
        """With default max_rounds=1, only round 1 fires: delegate once, no iteration rounds."""
        engine, db, tmpdir = _make_engine()
        task_id = "task-default-rounds"
        plan = OrchestrationPlan(
            summary="Test plan",
            sub_tasks=[SubTaskPlan("forge", "Task A", "Do A", "A done")],
        )
        assert plan.max_rounds == 1

        _setup_active_state(engine, task_id, plan)

        with (
            patch.object(engine, "_phase_plan"),
            patch.object(engine, "_phase_delegate") as mock_delegate,
            patch.object(engine, "_phase_delegate_iteration") as mock_delegate_iter,
            patch.object(engine, "_update_team_context_outcomes"),
            patch.object(engine, "_update_being_representations"),
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synthesize,
            patch.object(engine, "_all_reviews_approved", return_value=False),
        ):
            engine._orchestrate(task_id)

            mock_delegate.assert_called_once_with(task_id)
            mock_delegate_iter.assert_not_called()
            mock_review.assert_called_once_with(task_id)
            mock_synthesize.assert_called_once_with(task_id)

    def test_max_rounds_capped_at_4(self):
        """max_rounds is clamped to [1, 4]: values above 4 become 4, below 1 become 1."""
        sub = [SubTaskPlan("forge", "T", "I", "D")]

        plan_high = OrchestrationPlan(summary="Test", sub_tasks=sub, max_rounds=10)
        assert plan_high.max_rounds == 4

        plan_zero = OrchestrationPlan(summary="Test", sub_tasks=sub, max_rounds=0)
        assert plan_zero.max_rounds == 1

        plan_negative = OrchestrationPlan(summary="Test", sub_tasks=sub, max_rounds=-5)
        assert plan_negative.max_rounds == 1

        # Boundary checks: 1 and 4 should pass through unchanged
        plan_one = OrchestrationPlan(summary="Test", sub_tasks=sub, max_rounds=1)
        assert plan_one.max_rounds == 1

        plan_four = OrchestrationPlan(summary="Test", sub_tasks=sub, max_rounds=4)
        assert plan_four.max_rounds == 4

    def test_two_round_iteration(self):
        """With max_rounds=2 and reviews not all approved, round 2 fires via _phase_delegate_iteration."""
        engine, db, tmpdir = _make_engine()
        task_id = "task-two-rounds"
        plan = OrchestrationPlan(
            summary="Test plan",
            sub_tasks=[SubTaskPlan("forge", "Task A", "Do A", "A done")],
            synthesis_strategy="merge",
            max_rounds=2,
        )

        _setup_active_state(engine, task_id, plan)

        with (
            patch.object(engine, "_phase_plan"),
            patch.object(engine, "_phase_delegate") as mock_delegate,
            patch.object(engine, "_phase_delegate_iteration") as mock_delegate_iter,
            patch.object(engine, "_update_team_context_outcomes"),
            patch.object(engine, "_update_being_representations"),
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synthesize,
            patch.object(engine, "_all_reviews_approved", return_value=False),
        ):
            engine._orchestrate(task_id)

            # Round 1: _phase_delegate called
            mock_delegate.assert_called_once_with(task_id)
            # Round 2: _phase_delegate_iteration called with round_number=2
            mock_delegate_iter.assert_called_once_with(task_id, 2)
            # Review called after each round
            assert mock_review.call_count == 2
            mock_review.assert_has_calls([call(task_id), call(task_id)])
            # Synthesis called once at the end
            mock_synthesize.assert_called_once_with(task_id)

    def test_early_stop_when_all_approved(self):
        """With max_rounds=3, if all reviews approve after round 1, rounds 2+3 are skipped."""
        engine, db, tmpdir = _make_engine()
        task_id = "task-early-stop"
        plan = OrchestrationPlan(
            summary="Test plan",
            sub_tasks=[SubTaskPlan("forge", "Task A", "Do A", "A done")],
            synthesis_strategy="merge",
            max_rounds=3,
        )

        _setup_active_state(engine, task_id, plan)

        with (
            patch.object(engine, "_phase_plan"),
            patch.object(engine, "_phase_delegate") as mock_delegate,
            patch.object(engine, "_phase_delegate_iteration") as mock_delegate_iter,
            patch.object(engine, "_update_team_context_outcomes"),
            patch.object(engine, "_update_being_representations"),
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synthesize,
            patch.object(engine, "_all_reviews_approved", return_value=True),
        ):
            engine._orchestrate(task_id)

            # Only round 1 fires
            mock_delegate.assert_called_once_with(task_id)
            # Rounds 2 and 3 are skipped because all reviews approved
            mock_delegate_iter.assert_not_called()
            # Review called only once (round 1)
            mock_review.assert_called_once_with(task_id)
            # Synthesis still called at the end
            mock_synthesize.assert_called_once_with(task_id)
