"""Tests for Bug 2: failed tasks must not stay stuck as 'in_progress'.

Covers:
- Phase tracking in failure messages
- Board update retry on failure
- retry_task transition (failed → backlog)
- Partial result persistence on failure
- _auto_update_task_status logging instead of silent swallow
"""
from __future__ import annotations

import os
import tempfile
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
    return engine, db, tmpdir, dashboard, project_svc


def _setup_active_state(engine, task_id, plan, status=STATUS_PLANNING):
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "task_id": task_id,
        "goal": "Test goal for state machine",
        "orchestration_session": f"orchestration:{task_id}",
        "requester_session": "s1",
        "sender": "user",
        "status": status,
        "plan": plan,
        "subtask_ids": {},
        "subtask_outputs": {},
        "subtask_reviews": {},
        "created_at": now,
    }
    with engine._lock:
        engine._active[task_id] = state


class TestFailOrchestractionPhaseTracking:
    """_fail_orchestration records the phase that failed."""

    def test_planning_phase_failure_includes_phase(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-plan-fail"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        exc = RuntimeError("LLM planning error")
        engine._fail_orchestration(task_id, exc, STATUS_PLANNING)

        # Check that the failure message mentions the planning phase
        msg_call = dashboard.create_message.call_args
        assert msg_call is not None
        content = msg_call[1].get("content") or msg_call[0][0] if msg_call[0] else msg_call[1]["content"]
        assert "planning" in content.lower()

    def test_delegating_phase_failure_includes_phase(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-deleg-fail"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        engine._fail_orchestration(task_id, RuntimeError("timeout"), STATUS_DELEGATING)

        msg_call = dashboard.create_message.call_args
        content = msg_call[1].get("content", "")
        assert "delegating" in content.lower()

    def test_synthesizing_phase_failure_includes_phase(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-synth-fail"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        engine._fail_orchestration(task_id, RuntimeError("synthesis crash"), STATUS_SYNTHESIZING)

        msg_call = dashboard.create_message.call_args
        content = msg_call[1].get("content", "")
        assert "synthesizing" in content.lower()


class TestBoardUpdateRetry:
    """Board update retries when first attempt fails."""

    def test_board_update_retried_on_first_failure(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-retry-board"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        # First call raises, second succeeds
        dashboard.update_task.side_effect = [Exception("DB locked"), {"status": "failed"}]

        engine._fail_orchestration(task_id, RuntimeError("test"), STATUS_DELEGATING)

        # update_task should have been called twice
        assert dashboard.update_task.call_count == 2

    def test_board_update_succeeds_first_try(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-board-ok"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        dashboard.update_task.return_value = {"status": "failed"}

        engine._fail_orchestration(task_id, RuntimeError("test"), STATUS_PLANNING)

        # Only one call needed
        assert dashboard.update_task.call_count == 1


class TestFailOrchestractionHistoryEvent:
    """_fail_orchestration logs phase info in history and events."""

    def test_history_includes_phase(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-hist"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        engine._fail_orchestration(task_id, RuntimeError("oops"), STATUS_REVIEWING)

        # Check _log_task_history was called with phase
        history_call = dashboard._log_task_history.call_args
        assert history_call[0][1] == "orchestration_failed"
        assert history_call[0][2]["phase"] == STATUS_REVIEWING

    def test_event_includes_phase(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-evt"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        engine._fail_orchestration(task_id, RuntimeError("oops"), STATUS_DELEGATING)

        # Find the orchestration_update emit with phase info
        # (_set_status also emits orchestration_update but without phase)
        found = False
        for c in dashboard._emit_event.call_args_list:
            event_type = c[0][0] if c[0] else c[1].get("event_type")
            if event_type == "orchestration_update":
                payload = c[0][1] if len(c[0]) > 1 else c[1]
                if "phase" in payload:
                    assert payload["phase"] == STATUS_DELEGATING
                    found = True
                    break
        assert found, "No orchestration_update event with phase info emitted"


class TestPartialResultPersistence:
    """Partial results are saved before marking as failed."""

    def test_persist_task_result_called_on_failure(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-partial"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        with patch.object(engine, "_persist_task_result") as mock_persist:
            engine._fail_orchestration(task_id, RuntimeError("crash"), STATUS_DELEGATING)
            mock_persist.assert_called_once()
            # Verify the synthesis text indicates failure with phase
            args = mock_persist.call_args[0]
            assert args[0] == task_id
            assert "FAILED at delegating" in args[2]


class TestOrchestratePhaseTracking:
    """_orchestrate tracks current_phase and passes it to _fail_orchestration."""

    def test_planning_failure_tracked(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-orch-plan"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        with patch.object(engine, "_phase_plan", side_effect=RuntimeError("plan boom")), \
             patch.object(engine, "_fail_orchestration") as mock_fail:
            engine._orchestrate(task_id)
            mock_fail.assert_called_once()
            assert mock_fail.call_args[0][2] == STATUS_PLANNING

    def test_delegation_failure_tracked(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-orch-deleg"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        with patch.object(engine, "_phase_plan"), \
             patch.object(engine, "_phase_delegate", side_effect=RuntimeError("delegate boom")), \
             patch.object(engine, "_fail_orchestration") as mock_fail:
            engine._orchestrate(task_id)
            mock_fail.assert_called_once()
            assert mock_fail.call_args[0][2] == STATUS_DELEGATING

    def test_review_failure_tracked(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-orch-review"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        with patch.object(engine, "_phase_plan"), \
             patch.object(engine, "_phase_delegate"), \
             patch.object(engine, "_update_post_delegation", create=True), \
             patch.object(engine, "_update_team_context_outcomes"), \
             patch.object(engine, "_update_being_representations"), \
             patch.object(engine, "_phase_review", side_effect=RuntimeError("review boom")), \
             patch.object(engine, "_fail_orchestration") as mock_fail:
            engine._orchestrate(task_id)
            mock_fail.assert_called_once()
            assert mock_fail.call_args[0][2] == STATUS_REVIEWING

    def test_synthesis_failure_tracked(self):
        engine, db, tmpdir, dashboard, _ = _make_engine()
        task_id = "task-orch-synth"
        plan = OrchestrationPlan(
            summary="Plan", sub_tasks=[SubTaskPlan("forge", "A", "Do A", "A done")],
        )
        _setup_active_state(engine, task_id, plan)

        with patch.object(engine, "_phase_plan"), \
             patch.object(engine, "_phase_delegate"), \
             patch.object(engine, "_update_post_delegation", create=True), \
             patch.object(engine, "_update_team_context_outcomes"), \
             patch.object(engine, "_update_being_representations"), \
             patch.object(engine, "_phase_review"), \
             patch.object(engine, "_phase_synthesize", side_effect=RuntimeError("synth boom")), \
             patch.object(engine, "_fail_orchestration") as mock_fail:
            engine._orchestrate(task_id)
            mock_fail.assert_called_once()
            assert mock_fail.call_args[0][2] == STATUS_SYNTHESIZING


class TestRetryTask:
    """DashboardService.retry_task transitions failed → backlog."""

    def test_retry_failed_task(self):
        from bomba_sr.dashboard.service import DashboardService
        db = RuntimeDB(os.path.join(tempfile.mkdtemp(), "runtime.db"))
        svc = DashboardService.__new__(DashboardService)
        svc.db = db
        svc.bridge = None
        svc.project_service = None
        svc.orchestration_engine = None
        svc._sse_clients = []

        project_svc = MagicMock()
        project_svc.get_task.return_value = {"task_id": "t1", "status": "failed"}

        # Mock update_task to return the updated task
        with patch.object(svc, "update_task", return_value={"id": "t1", "status": "backlog"}) as mock_update, \
             patch.object(svc, "_log_task_history"):
            result = svc.retry_task(project_svc, "t1")
            assert result is not None
            assert result["status"] == "backlog"
            mock_update.assert_called_once_with(
                project_service=project_svc, task_id="t1", status="backlog",
            )

    def test_retry_non_failed_task_rejected(self):
        from bomba_sr.dashboard.service import DashboardService
        db = RuntimeDB(os.path.join(tempfile.mkdtemp(), "runtime.db"))
        svc = DashboardService.__new__(DashboardService)
        svc.db = db
        svc.bridge = None
        svc.project_service = None
        svc.orchestration_engine = None
        svc._sse_clients = []

        project_svc = MagicMock()
        project_svc.get_task.return_value = {"task_id": "t1", "status": "in_progress"}

        result = svc.retry_task(project_svc, "t1")
        assert result is None

    def test_retry_nonexistent_task_returns_none(self):
        from bomba_sr.dashboard.service import DashboardService
        db = RuntimeDB(os.path.join(tempfile.mkdtemp(), "runtime.db"))
        svc = DashboardService.__new__(DashboardService)
        svc.db = db
        svc.bridge = None
        svc.project_service = None
        svc.orchestration_engine = None
        svc._sse_clients = []

        project_svc = MagicMock()
        project_svc.get_task.side_effect = ValueError("not found")

        result = svc.retry_task(project_svc, "t-nonexist")
        assert result is None


class TestAutoUpdateTaskStatusLogging:
    """_auto_update_task_status logs failures instead of silently swallowing."""

    def test_logs_on_failure(self):
        from bomba_sr.dashboard.service import DashboardService
        db = RuntimeDB(os.path.join(tempfile.mkdtemp(), "runtime.db"))
        svc = DashboardService.__new__(DashboardService)
        svc.db = db
        svc.bridge = None
        svc.orchestration_engine = None
        svc._sse_clients = []

        project_svc = MagicMock()
        svc.project_service = project_svc

        with patch.object(svc, "update_task", side_effect=Exception("DB error")), \
             patch("bomba_sr.dashboard.service.log") as mock_log:
            svc._auto_update_task_status("task-123", "failed")
            mock_log.warning.assert_called_once()
            assert "task-12" in mock_log.warning.call_args[0][1]

    def test_logs_when_no_project_service(self):
        from bomba_sr.dashboard.service import DashboardService
        db = RuntimeDB(os.path.join(tempfile.mkdtemp(), "runtime.db"))
        svc = DashboardService.__new__(DashboardService)
        svc.db = db
        svc.bridge = None
        svc.orchestration_engine = None
        svc._sse_clients = []
        svc.project_service = None

        with patch("bomba_sr.dashboard.service.log") as mock_log:
            svc._auto_update_task_status("task-456", "done")
            mock_log.warning.assert_called_once()
