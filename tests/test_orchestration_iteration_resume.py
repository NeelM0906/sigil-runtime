"""Tests for resuming mid-iteration and sequential iteration strategy."""
from __future__ import annotations

import json
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
    dashboard.get_being.return_value = {}
    project_svc = MagicMock()
    engine = OrchestrationEngine(
        bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
    )
    return engine, db, tmpdir


def _insert_orchestration_row(db, task_id, status, timestamp, plan_json=None, subtask_ids="{}", subtask_reviews="{}"):
    db.execute_commit(
        """INSERT INTO orchestration_state
            (task_id, goal, orch_session_id, requester_session,
             sender, status, plan_json, subtask_ids,
             subtask_reviews, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (task_id, "Test goal", f"orchestration:{task_id}",
         "s1", "user", status, plan_json, subtask_ids,
         subtask_reviews, timestamp, timestamp),
    )


# ---------------------------------------------------------------------------
# Test 9: Resume mid-iteration
# ---------------------------------------------------------------------------


class TestResumeMidIteration:
    def test_resume_mid_iteration(self):
        """Resuming from delegating_round_2 should skip round 1 and continue
        from round 2 through max_rounds, calling synthesize once at the end."""
        engine, db, tmpdir = _make_engine()
        task_id = "task-resume-iter"

        # Build a plan with max_rounds=3, 2 beings, strategy="merge"
        plan = OrchestrationPlan(
            summary="Multi-round merge plan",
            sub_tasks=[
                SubTaskPlan(
                    being_id="forge",
                    title="Forge analysis",
                    instructions="Analyze the data",
                    done_when="Analysis complete",
                ),
                SubTaskPlan(
                    being_id="scholar",
                    title="Scholar review",
                    instructions="Review the analysis",
                    done_when="Review complete",
                ),
            ],
            synthesis_strategy="merge",
            max_rounds=3,
        )
        plan_json = json.dumps(plan.to_dict())

        now = datetime.now(timezone.utc).isoformat()

        # Create the orchestration_state table (engine __init__ does this via mock,
        # so we need to do it explicitly for our real DB).
        db.script(
            """
            CREATE TABLE IF NOT EXISTS orchestration_state (
                task_id           TEXT PRIMARY KEY,
                goal              TEXT NOT NULL,
                orch_session_id   TEXT NOT NULL,
                requester_session TEXT NOT NULL,
                sender            TEXT NOT NULL,
                status            TEXT NOT NULL,
                plan_json         TEXT,
                subtask_ids       TEXT NOT NULL DEFAULT '{}',
                subtask_reviews   TEXT NOT NULL DEFAULT '{}',
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL
            );
            """
        )

        # Insert orchestration row with status "delegating_round_2"
        _insert_orchestration_row(
            db, task_id, "delegating_round_2", now, plan_json=plan_json,
        )

        # Build the state dict manually and populate _active
        state = {
            "task_id": task_id,
            "goal": "Test goal",
            "orchestration_session": f"orchestration:{task_id}",
            "requester_session": "s1",
            "sender": "user",
            "status": "delegating_round_2",
            "plan": plan,
            "subtask_ids": {},
            "subtask_outputs": {},
            "subtask_reviews": {},
            "created_at": now,
        }
        engine._active[task_id] = state

        # Patch all downstream phase methods
        with (
            patch.object(engine, "_reload_outputs_from_shared_memory") as mock_reload,
            patch.object(engine, "_phase_delegate_iteration") as mock_delegate_iter,
            patch.object(engine, "_update_post_delegation") as mock_update_post,
            patch.object(engine, "_phase_review") as mock_review,
            patch.object(engine, "_phase_synthesize") as mock_synthesize,
            patch.object(engine, "_all_reviews_approved", return_value=False) as mock_approved,
            patch.object(engine, "_phase_delegate") as mock_delegate_r1,
            patch.object(engine, "_resume_delegation") as mock_resume_deleg,
        ):
            engine._resume_from_status(task_id, state)

            # _reload_outputs_from_shared_memory called once to restore prior outputs
            mock_reload.assert_called_once_with(task_id, state)

            # _phase_delegate_iteration called for rounds 2 and 3 (NOT round 1)
            assert mock_delegate_iter.call_count == 2
            mock_delegate_iter.assert_any_call(task_id, 2)
            mock_delegate_iter.assert_any_call(task_id, 3)

            # Round 1 delegation methods should NOT be called
            mock_delegate_r1.assert_not_called()
            mock_resume_deleg.assert_not_called()

            # _phase_review called twice (once per round)
            assert mock_review.call_count == 2

            # _update_post_delegation called twice (once per round)
            assert mock_update_post.call_count == 2

            # _all_reviews_approved called once (for rn=2 only;
            # for rn=3, rn < max_rounds is False so it short-circuits)
            assert mock_approved.call_count == 1

            # _phase_synthesize called once at the end
            mock_synthesize.assert_called_once_with(task_id)


# ---------------------------------------------------------------------------
# Test 10: Sequential iteration strategy
# ---------------------------------------------------------------------------


class TestSequentialIteration:
    def test_iteration_with_sequential_strategy(self):
        """For sequential strategy, _phase_delegate_iteration processes beings
        one at a time. The second being's message should include the first
        being's prior output from shared memory."""
        engine, db, tmpdir = _make_engine()
        task_id = "task-seq-iter"

        # Build a plan with strategy="sequential", max_rounds=2, 2 beings
        plan = OrchestrationPlan(
            summary="Sequential iteration plan",
            sub_tasks=[
                SubTaskPlan(
                    being_id="forge",
                    title="Forge task",
                    instructions="Write the draft",
                    done_when="Draft complete",
                ),
                SubTaskPlan(
                    being_id="scholar",
                    title="Scholar task",
                    instructions="Refine the draft",
                    done_when="Refinement complete",
                ),
            ],
            synthesis_strategy="sequential",
            max_rounds=2,
        )

        now = datetime.now(timezone.utc).isoformat()

        # Populate engine._active with the state
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
        engine._active[task_id] = state

        # Set up protocol mock for shared memory reads
        protocol = MagicMock()
        protocol.read_shared_memory.return_value = [
            {"writer_agent_id": "forge", "content": "Forge R1 output"},
            {"writer_agent_id": "scholar", "content": "Scholar R1 output"},
        ]
        engine.protocol = protocol

        # Set up subagent_orch mock
        engine.subagent_orch = MagicMock()
        engine._orchestration_worker = MagicMock()

        # Track calls to _execute_subtask_with_message
        execute_calls = []
        run_counter = [0]

        def mock_execute(parent_task_id, sub, message, idempotency_suffix=""):
            run_counter[0] += 1
            run_id = f"run-{run_counter[0]}"
            execute_calls.append({
                "parent_task_id": parent_task_id,
                "being_id": sub.being_id,
                "message": message,
                "idempotency_suffix": idempotency_suffix,
            })
            return run_id

        with (
            patch.object(engine, "_execute_subtask_with_message", side_effect=mock_execute) as mock_exec,
            patch.object(engine, "_await_run_completion", return_value={"status": "completed"}) as mock_await,
            patch.object(engine, "_on_subtask_completed") as mock_on_completed,
            patch.object(engine, "_db_update_subtask_ids") as mock_db_update,
        ):
            engine._phase_delegate_iteration(task_id, 2)

            # _execute_subtask_with_message called twice (once per being, sequentially)
            assert mock_exec.call_count == 2

            # Both calls should have idempotency_suffix containing ":round:2"
            assert execute_calls[0]["idempotency_suffix"] == ":round:2"
            assert execute_calls[1]["idempotency_suffix"] == ":round:2"

            # First call is for forge, second for scholar
            assert execute_calls[0]["being_id"] == "forge"
            assert execute_calls[1]["being_id"] == "scholar"

            # Both messages should reference Round 2
            assert "Round 2" in execute_calls[0]["message"]
            assert "Round 2" in execute_calls[1]["message"]

            # Forge (first being) should NOT have prior outputs from other beings
            # because no beings come before forge in the plan order.
            # _collect_prior_outputs_from_shared_memory returns {} for forge,
            # so _build_iteration_message skips the "Context from previous round" block.
            forge_message = execute_calls[0]["message"]
            assert "scholar's output" not in forge_message
            assert "Context from previous round" not in forge_message

            # Scholar (second being) should include forge's prior output
            # because _collect_prior_outputs_from_shared_memory returns
            # {"forge": "Forge R1 output"} for scholar
            scholar_message = execute_calls[1]["message"]
            assert "forge's output" in scholar_message
            assert "Forge R1 output" in scholar_message

            # Verify scholar's message includes the task instructions
            assert "Refine the draft" in scholar_message

            # _await_run_completion called twice
            assert mock_await.call_count == 2

            # _on_subtask_completed called twice
            assert mock_on_completed.call_count == 2

            # protocol.read_shared_memory was called (by _collect_prior_outputs_from_shared_memory)
            assert protocol.read_shared_memory.call_count >= 2
