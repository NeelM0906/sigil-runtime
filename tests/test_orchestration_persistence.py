"""Tests for orchestration engine SQLite persistence layer.

Covers:
  - State insert + load round-trip returns equivalent data
  - Corrupted JSON in DB returns None (Issue 12 fix)
  - cleanup_orphaned_orchestrations() marks stale tasks as failed
  - State survives simulated restart (save, create new engine, load)
  - subtask_ids persistence round-trip (Issue 13)
  - _get_state() returns deep copy (Issue 15 / TOCTOU fix)
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from bomba_sr.orchestration.engine import (
    OrchestrationEngine,
    OrchestrationPlan,
    SubTaskPlan,
    STATUS_PLANNING,
    STATUS_DELEGATING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from bomba_sr.storage.db import RuntimeDB


# ---------------------------------------------------------------------------
# Helper: create a minimal engine backed by a real SQLite DB
# ---------------------------------------------------------------------------

def _make_engine(db: RuntimeDB | None = None, tmpdir: str | None = None):
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


# ---------------------------------------------------------------------------
# Issue 11: State insert + load round-trip
# ---------------------------------------------------------------------------

class TestStateRoundTrip:
    """Verify that inserting state and loading it back produces equivalent data."""

    def test_insert_and_load_basic_state(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-rt-1",
            "goal": "Round-trip test goal",
            "orchestration_session": "orchestration:task-rt-1",
            "requester_session": "mc-chat-prime",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-rt-1", state, now)

        loaded = engine._db_load_state("task-rt-1")
        assert loaded is not None
        assert loaded["task_id"] == "task-rt-1"
        assert loaded["goal"] == "Round-trip test goal"
        assert loaded["orchestration_session"] == "orchestration:task-rt-1"
        assert loaded["requester_session"] == "mc-chat-prime"
        assert loaded["sender"] == "user"
        assert loaded["status"] == STATUS_PLANNING
        assert loaded["plan"] is None
        assert loaded["subtask_ids"] == {}
        assert loaded["subtask_reviews"] == {}

    def test_insert_and_load_with_plan(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-rt-2",
            "goal": "Plan round-trip test",
            "orchestration_session": "orchestration:task-rt-2",
            "requester_session": "mc-chat-prime",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-rt-2", state, now)

        # Now update with a plan
        plan = OrchestrationPlan(
            summary="Test plan",
            sub_tasks=[
                SubTaskPlan("forge", "Research", "Do research", "List of 5"),
                SubTaskPlan("memory", "Recall", "Check memory", "Results found"),
            ],
            synthesis_strategy="merge",
        )
        engine._db_update_plan("task-rt-2", plan)

        loaded = engine._db_load_state("task-rt-2")
        assert loaded is not None
        assert loaded["plan"] is not None
        assert loaded["plan"].summary == "Test plan"
        assert len(loaded["plan"].sub_tasks) == 2
        assert loaded["plan"].sub_tasks[0].being_id == "forge"
        assert loaded["plan"].sub_tasks[1].being_id == "memory"
        assert loaded["plan"].synthesis_strategy == "merge"

    def test_insert_and_load_with_reviews(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-rt-3",
            "goal": "Review round-trip test",
            "orchestration_session": "orchestration:task-rt-3",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_DELEGATING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-rt-3", state, now)

        # Merge reviews (outputs now live in shared_working_memory_writes)
        engine._db_merge_subtask_review("task-rt-3", "forge", {
            "approved": True, "feedback": "", "quality_score": 0.9, "notes": "Good",
        })

        loaded = engine._db_load_state("task-rt-3")
        assert loaded is not None
        assert loaded["subtask_outputs"] == {}  # not persisted to DB
        assert loaded["subtask_reviews"]["forge"]["approved"] is True
        assert loaded["subtask_reviews"]["forge"]["quality_score"] == 0.9

    def test_load_nonexistent_returns_none(self):
        engine, db, _ = _make_engine()
        assert engine._db_load_state("nonexistent-task") is None


# ---------------------------------------------------------------------------
# Issue 12: Corrupted JSON in DB returns None
# ---------------------------------------------------------------------------

class TestCorruptPlanJson:
    """After Issue 12 fix, corrupt plan_json should log ERROR and return None."""

    def test_corrupt_plan_json_returns_none(self, caplog):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()

        # Insert a row with valid data first
        state = {
            "task_id": "task-corrupt-1",
            "goal": "Corrupt test",
            "orchestration_session": "orchestration:task-corrupt-1",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-corrupt-1", state, now)

        # Manually corrupt the plan_json column
        db.execute_commit(
            "UPDATE orchestration_state SET plan_json = ? WHERE task_id = ?",
            ("{not valid json!!", "task-corrupt-1"),
        )

        with caplog.at_level(logging.ERROR):
            result = engine._db_load_state("task-corrupt-1")

        # Should return None for unrecoverable corruption
        assert result is None

        # Should have logged an ERROR
        error_msgs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert any("Corrupt plan_json" in r.message for r in error_msgs), (
            f"Expected ERROR log about corrupt plan_json, got: {[r.message for r in error_msgs]}"
        )

    def test_null_plan_json_is_valid(self):
        """A NULL plan_json (no plan yet) should load normally with plan=None."""
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-null-plan",
            "goal": "Null plan test",
            "orchestration_session": "orchestration:task-null-plan",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-null-plan", state, now)

        loaded = engine._db_load_state("task-null-plan")
        assert loaded is not None
        assert loaded["plan"] is None

    def test_empty_string_plan_json_is_valid(self):
        """An empty string plan_json should load normally with plan=None."""
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-empty-plan",
            "goal": "Empty plan test",
            "orchestration_session": "orchestration:task-empty-plan",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-empty-plan", state, now)

        # Set plan_json to empty string
        db.execute_commit(
            "UPDATE orchestration_state SET plan_json = '' WHERE task_id = ?",
            ("task-empty-plan",),
        )

        loaded = engine._db_load_state("task-empty-plan")
        assert loaded is not None
        assert loaded["plan"] is None


# ---------------------------------------------------------------------------
# Issue 11: cleanup_orphaned_orchestrations marks stale tasks as failed
# ---------------------------------------------------------------------------

class TestCleanupOrphaned:
    """Verify cleanup_orphaned_orchestrations() marks stale in-progress tasks."""

    def test_cleanup_marks_stale_as_failed(self):
        engine, db, _ = _make_engine()
        # Insert a stale task (updated_at 25 hours ago — past the 24h resume cutoff)
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
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
                "task-stale-1", "Stale goal", "orchestration:task-stale-1",
                "s1", "user", STATUS_DELEGATING, None, "{}", "{}",
                stale_time, stale_time,
            ),
        )

        cleaned = engine.cleanup_orphaned_orchestrations()
        assert cleaned == 1

        # Verify the task is now marked as failed
        row = db.execute(
            "SELECT status FROM orchestration_state WHERE task_id = ?",
            ("task-stale-1",),
        ).fetchone()
        assert row["status"] == STATUS_FAILED

    def test_cleanup_ignores_completed_tasks(self):
        engine, db, _ = _make_engine()
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

        db.execute_commit(
            """
            INSERT INTO orchestration_state
                (task_id, goal, orch_session_id, requester_session,
                 sender, status, plan_json, subtask_ids,
                 subtask_reviews, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "task-done-1", "Completed goal", "orchestration:task-done-1",
                "s1", "user", STATUS_COMPLETED, None, "{}", "{}",
                stale_time, stale_time,
            ),
        )

        cleaned = engine.cleanup_orphaned_orchestrations()
        assert cleaned == 0

    def test_cleanup_resumes_recent_tasks(self):
        """Recent non-terminal tasks (< 24h) are attempted for resume, not marked failed."""
        engine, db, _ = _make_engine()
        recent_time = datetime.now(timezone.utc).isoformat()

        db.execute_commit(
            """
            INSERT INTO orchestration_state
                (task_id, goal, orch_session_id, requester_session,
                 sender, status, plan_json, subtask_ids,
                 subtask_reviews, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "task-recent-1", "Recent goal", "orchestration:task-recent-1",
                "s1", "user", STATUS_DELEGATING, None, "{}", "{}",
                recent_time, recent_time,
            ),
        )

        processed = engine.cleanup_orphaned_orchestrations()
        # Recent non-terminal tasks are now resumed (processed), not ignored
        assert processed == 1


# ---------------------------------------------------------------------------
# Issue 11: State survives simulated restart
# ---------------------------------------------------------------------------

class TestRestartSurvival:
    """Verify state persists across engine restarts (new engine instance, same DB)."""

    def test_state_survives_restart(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "runtime.db")

        # Engine 1: insert state
        db1 = RuntimeDB(db_path)
        engine1, _, _ = _make_engine(db=db1, tmpdir=tmpdir)

        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-restart-1",
            "goal": "Survive restart",
            "orchestration_session": "orchestration:task-restart-1",
            "requester_session": "mc-chat-prime",
            "sender": "user",
            "status": STATUS_DELEGATING,
            "plan": None,
            "subtask_ids": {"forge": "task-restart-1"},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine1._db_insert_state("task-restart-1", state, now)

        # Update with a plan
        plan = OrchestrationPlan(
            summary="Restart test plan",
            sub_tasks=[SubTaskPlan("forge", "Work", "Do work", "Done")],
            synthesis_strategy="merge",
        )
        engine1._db_update_plan("task-restart-1", plan)

        # Update subtask_ids
        engine1._db_update_subtask_ids("task-restart-1", {"forge": "task-restart-1"})

        # Close DB to simulate shutdown
        db1.close()

        # Engine 2: new instance, same DB file
        db2 = RuntimeDB(db_path)
        engine2, _, _ = _make_engine(db=db2, tmpdir=tmpdir)

        loaded = engine2._db_load_state("task-restart-1")
        assert loaded is not None
        assert loaded["goal"] == "Survive restart"
        assert loaded["status"] == STATUS_DELEGATING
        assert loaded["plan"] is not None
        assert loaded["plan"].summary == "Restart test plan"
        assert loaded["plan"].sub_tasks[0].being_id == "forge"
        assert loaded["subtask_ids"] == {"forge": "task-restart-1"}
        # subtask_outputs are no longer persisted to DB (live in shared_working_memory_writes)
        assert loaded["subtask_outputs"] == {}

        db2.close()


# ---------------------------------------------------------------------------
# Issue 13: subtask_ids persistence
# ---------------------------------------------------------------------------

class TestSubtaskIdsPersistence:
    """Verify subtask_ids are persisted and loaded correctly."""

    def test_subtask_ids_round_trip(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-ids-1",
            "goal": "Subtask IDs test",
            "orchestration_session": "orchestration:task-ids-1",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_DELEGATING,
            "plan": None,
            "subtask_ids": {"forge": "task-ids-1", "memory": "task-ids-1"},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-ids-1", state, now)

        loaded = engine._db_load_state("task-ids-1")
        assert loaded is not None
        assert loaded["subtask_ids"] == {"forge": "task-ids-1", "memory": "task-ids-1"}

    def test_subtask_ids_update(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-ids-2",
            "goal": "Update IDs test",
            "orchestration_session": "orchestration:task-ids-2",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._db_insert_state("task-ids-2", state, now)

        # Update subtask_ids
        engine._db_update_subtask_ids("task-ids-2", {
            "forge": "task-ids-2",
            "scholar": "task-ids-2",
        })

        loaded = engine._db_load_state("task-ids-2")
        assert loaded is not None
        assert loaded["subtask_ids"]["forge"] == "task-ids-2"
        assert loaded["subtask_ids"]["scholar"] == "task-ids-2"

    def test_subtask_ids_column_in_schema(self):
        """The orchestration_state table should have a subtask_ids column."""
        engine, db, _ = _make_engine()
        # Check schema via pragma
        cols = db.execute("PRAGMA table_info(orchestration_state)").fetchall()
        col_names = [c["name"] for c in cols]
        assert "subtask_ids" in col_names


# ---------------------------------------------------------------------------
# Issue 15: _get_state() returns deep copy (TOCTOU fix)
# ---------------------------------------------------------------------------

class TestGetStateDeepCopy:
    """Verify _get_state() returns an isolated snapshot, not a mutable reference."""

    def test_get_state_returns_copy(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-copy-1",
            "goal": "Deep copy test",
            "orchestration_session": "orchestration:task-copy-1",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        # Put it in the active cache
        with engine._lock:
            engine._active["task-copy-1"] = state

        # Get state via the public method
        snapshot = engine._get_state("task-copy-1")

        # Mutate the snapshot
        snapshot["status"] = "MUTATED"
        snapshot["subtask_reviews"]["forge"] = {"approved": True}

        # Verify the canonical state is unchanged
        with engine._lock:
            canonical = engine._active["task-copy-1"]
        assert canonical["status"] == STATUS_PLANNING
        assert "forge" not in canonical["subtask_reviews"]

    def test_get_state_two_calls_independent(self):
        engine, db, _ = _make_engine()
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": "task-copy-2",
            "goal": "Independence test",
            "orchestration_session": "orchestration:task-copy-2",
            "requester_session": "s1",
            "sender": "user",
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},
            "subtask_outputs": {},  # in-memory only, not persisted
            "subtask_reviews": {},
            "created_at": now,
        }
        with engine._lock:
            engine._active["task-copy-2"] = state

        snap1 = engine._get_state("task-copy-2")
        snap2 = engine._get_state("task-copy-2")

        # Mutating snap1 should not affect snap2
        snap1["goal"] = "MUTATED"
        assert snap2["goal"] == "Independence test"
