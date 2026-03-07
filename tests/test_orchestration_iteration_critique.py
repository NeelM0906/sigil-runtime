"""Tests for critique strategy and iteration mechanics."""
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
    STATUS_DELEGATING,
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
    dashboard.get_being.return_value = {}
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
        "status": STATUS_DELEGATING,
        "plan": plan,
        "subtask_ids": {},
        "subtask_outputs": {},
        "subtask_reviews": {},
        "created_at": now,
    }
    with engine._lock:
        engine._active[task_id] = state


class TestCritiqueStrategy:
    """Tests for the critique synthesis strategy message building and delegation."""

    def test_critique_strategy_round_2_message(self):
        """_build_critique_round_message produces a message containing round number,
        original task, labeled own/other outputs, and the actual output content."""
        engine, db, tmpdir = _make_engine()

        sub_forge = SubTaskPlan("forge", "Task A", "Do A thoroughly", "A done")
        sub_scholar = SubTaskPlan("scholar", "Task B", "Do B carefully", "B done")

        plan = OrchestrationPlan(
            summary="Test critique plan",
            sub_tasks=[sub_forge, sub_scholar],
            synthesis_strategy="critique",
            max_rounds=2,
        )

        all_prior_outputs = {
            "forge": "Forge R1 output",
            "scholar": "Scholar R1 output",
        }

        message = engine._build_critique_round_message(sub_forge, 2, all_prior_outputs)

        # Round number is included
        assert "Round 2" in message
        # The original task instructions are included
        assert "Your original task:" in message
        assert "Do A thoroughly" in message
        # Forge's own output is labeled as "YOUR PREVIOUS OUTPUT"
        assert "YOUR PREVIOUS OUTPUT" in message
        # Scholar's output is labeled with their being_id
        assert "scholar's output" in message
        # The actual output content is present
        assert "Forge R1 output" in message
        assert "Scholar R1 output" in message

    def test_critique_every_being_sees_all_outputs(self):
        """In a critique round, _phase_delegate_iteration calls _execute_subtask_with_message
        once per being, and each call's message contains ALL beings' outputs."""
        engine, db, tmpdir = _make_engine()

        sub_forge = SubTaskPlan("forge", "Task A", "Do A", "A done")
        sub_scholar = SubTaskPlan("scholar", "Task B", "Do B", "B done")
        sub_herald = SubTaskPlan("herald", "Task C", "Do C", "C done")

        task_id = "task-critique-all-see"
        plan = OrchestrationPlan(
            summary="Three-being critique",
            sub_tasks=[sub_forge, sub_scholar, sub_herald],
            synthesis_strategy="critique",
            max_rounds=2,
        )

        _setup_active_state(engine, task_id, plan)

        # Set up protocol mock so _read_all_committed_outputs returns 3 outputs
        engine.protocol = MagicMock()
        engine.protocol.read_shared_memory.return_value = [
            {"writer_agent_id": "forge", "content": "Forge output text"},
            {"writer_agent_id": "scholar", "content": "Scholar output text"},
            {"writer_agent_id": "herald", "content": "Herald output text"},
        ]

        # Set up subagent_orch so _execute_subtask_with_message doesn't fail on None check
        engine.subagent_orch = MagicMock()
        engine._orchestration_worker = MagicMock()

        # Track calls to _execute_subtask_with_message
        captured_calls = []

        def fake_execute(parent_task_id, sub, message, idempotency_suffix=""):
            captured_calls.append({
                "parent_task_id": parent_task_id,
                "being_id": sub.being_id,
                "message": message,
                "idempotency_suffix": idempotency_suffix,
            })
            return f"run-{sub.being_id}"

        with (
            patch.object(engine, "_execute_subtask_with_message", side_effect=fake_execute),
            patch.object(engine, "_await_run_completion", return_value={"status": "completed"}),
            patch.object(engine, "_on_subtask_completed"),
            patch.object(engine, "_db_update_subtask_ids"),
        ):
            engine._phase_delegate_iteration(task_id, 2)

        # Should have been called once per being (3 times)
        assert len(captured_calls) == 3

        # Each being's message must contain ALL three beings' output content
        for c in captured_calls:
            msg = c["message"]
            assert "Forge output text" in msg, (
                f"Message for {c['being_id']} missing Forge output"
            )
            assert "Scholar output text" in msg, (
                f"Message for {c['being_id']} missing Scholar output"
            )
            assert "Herald output text" in msg, (
                f"Message for {c['being_id']} missing Herald output"
            )

        # Verify the correct beings were targeted
        called_beings = [c["being_id"] for c in captured_calls]
        assert called_beings == ["forge", "scholar", "herald"]


class TestIterationMechanics:
    """Tests for shared memory reads and idempotency across rounds."""

    def test_shared_memory_round_2_supersedes_round_1(self):
        """_read_all_committed_outputs deduplicates by writer_agent_id, keeping the
        newest entry (first in the list) so round 2 output supersedes round 1."""
        engine, db, tmpdir = _make_engine()

        engine.protocol = MagicMock()
        engine.protocol.read_shared_memory.return_value = [
            # Newest first — round 2 output for forge comes before round 1
            {"writer_agent_id": "forge", "content": "Round 2 output"},
            {"writer_agent_id": "forge", "content": "Round 1 output"},
            {"writer_agent_id": "scholar", "content": "Scholar output"},
        ]

        result = engine._read_all_committed_outputs("task-supersede")

        # forge's Round 2 output wins (first encountered)
        assert result == {
            "forge": "Round 2 output",
            "scholar": "Scholar output",
        }
        # Verify the older forge output was NOT included
        assert result["forge"] != "Round 1 output"

        # Verify protocol was called with correct args
        engine.protocol.read_shared_memory.assert_called_once_with(
            ticket_id="task-supersede", scope="committed",
        )

    def test_idempotency_keys_differ_across_rounds(self):
        """_execute_subtask_with_message generates distinct idempotency keys when
        called with different idempotency_suffix values for different rounds."""
        engine, db, tmpdir = _make_engine()

        task_id = "task-idem-rounds-01"
        sub_forge = SubTaskPlan("forge", "Task A", "Do A", "A done")

        plan = OrchestrationPlan(
            summary="Idempotency test",
            sub_tasks=[sub_forge],
            synthesis_strategy="critique",
            max_rounds=2,
        )

        _setup_active_state(engine, task_id, plan)

        # Set up required mocks for _execute_subtask_with_message
        engine.subagent_orch = MagicMock()
        engine.protocol = MagicMock()
        engine._orchestration_worker = MagicMock()

        # Track the idempotency keys from SubAgentTask passed to spawn_async
        captured_keys = []

        def capture_spawn(task, **kwargs):
            captured_keys.append(task.idempotency_key)
            handle = MagicMock()
            handle.run_id = f"run-{len(captured_keys)}"
            return handle

        engine.subagent_orch.spawn_async.side_effect = capture_spawn

        # Call for round 1
        run_id_1 = engine._execute_subtask_with_message(
            task_id, sub_forge, "Round 1 message", idempotency_suffix=":round:1",
        )
        # Call for round 2
        run_id_2 = engine._execute_subtask_with_message(
            task_id, sub_forge, "Round 2 message", idempotency_suffix=":round:2",
        )

        assert len(captured_keys) == 2
        key1, key2 = captured_keys

        # The two idempotency keys must be different
        assert key1 != key2, (
            f"Idempotency keys should differ across rounds: {key1!r} == {key2!r}"
        )

        # Key structure: "{parent_task_id}:{being_id}{idempotency_suffix}"
        assert key1.endswith(":round:1"), f"Expected key1 to end with ':round:1', got {key1!r}"
        assert key2.endswith(":round:2"), f"Expected key2 to end with ':round:2', got {key2!r}"

        # Both keys share the same prefix (task_id:being_id)
        expected_prefix = f"{task_id}:forge"
        assert key1.startswith(expected_prefix), (
            f"Expected key1 to start with {expected_prefix!r}, got {key1!r}"
        )
        assert key2.startswith(expected_prefix), (
            f"Expected key2 to start with {expected_prefix!r}, got {key2!r}"
        )
