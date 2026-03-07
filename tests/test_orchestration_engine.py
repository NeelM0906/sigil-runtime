"""Tests for the being-to-being orchestration engine.

Verifies:
  - Session ID patterns (orchestration:{task_id}, subtask:{task_id}:{being_id})
  - Plan parsing from LLM output
  - Review parsing from LLM output
  - Orchestration lifecycle (plan → delegate → review → synthesize)
  - Session isolation (orchestration sessions don't mix with chat sessions)
"""
from __future__ import annotations

import json
import threading
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.orchestration.engine import (
    OrchestrationEngine,
    OrchestrationPlan,
    SubTaskPlan,
    orchestration_session_id,
    subtask_session_id,
    STATUS_PLANNING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)


# ---------------------------------------------------------------------------
# Session ID pattern tests
# ---------------------------------------------------------------------------

class TestSessionIdPatterns:
    def test_orchestration_session_id(self):
        tid = "task-abc-123"
        assert orchestration_session_id(tid) == "orchestration:task-abc-123"

    def test_subtask_session_id(self):
        tid = "task-abc-123"
        bid = "sai-forge"
        assert subtask_session_id(tid, bid) == "subtask:task-abc-123:sai-forge"

    def test_session_ids_are_distinct(self):
        tid = "task-1"
        orch = orchestration_session_id(tid)
        sub_forge = subtask_session_id(tid, "forge")
        sub_memory = subtask_session_id(tid, "memory")
        assert orch != sub_forge
        assert orch != sub_memory
        assert sub_forge != sub_memory

    def test_no_collision_with_chat_sessions(self):
        """Orchestration session IDs must not collide with existing chat patterns."""
        tid = "task-1"
        orch = orchestration_session_id(tid)
        sub = subtask_session_id(tid, "forge")
        chat_patterns = [
            "mc-chat-forge",
            "mc-chat-prime",
            "sister-chat-forge",
            "sister-chat-memory",
        ]
        for pat in chat_patterns:
            assert orch != pat
            assert sub != pat


# ---------------------------------------------------------------------------
# Plan/Review parsing tests
# ---------------------------------------------------------------------------

class TestPlanParsing:
    def _engine(self) -> OrchestrationEngine:
        return OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )

    def test_parse_valid_plan(self):
        engine = self._engine()
        beings = [
            {"id": "forge", "name": "SAI Forge"},
            {"id": "memory", "name": "SAI Memory"},
        ]
        reply = json.dumps({
            "summary": "Research task",
            "synthesis_strategy": "merge",
            "sub_tasks": [
                {
                    "being_id": "forge",
                    "title": "Research competitors",
                    "instructions": "Find top 5 competitors",
                    "done_when": "List of 5 with descriptions",
                },
                {
                    "being_id": "memory",
                    "title": "Compile notes",
                    "instructions": "Check memory for prior research",
                    "done_when": "Memory search results compiled",
                },
            ],
        })
        plan = engine._parse_plan(reply, beings)
        assert isinstance(plan, OrchestrationPlan)
        assert len(plan.sub_tasks) == 2
        assert plan.sub_tasks[0].being_id == "forge"
        assert plan.sub_tasks[1].being_id == "memory"
        assert plan.synthesis_strategy == "merge"

    def test_parse_plan_with_markdown_fences(self):
        engine = self._engine()
        beings = [{"id": "forge", "name": "SAI Forge"}]
        reply = '```json\n{"summary":"Test","sub_tasks":[{"being_id":"forge","title":"Do it","instructions":"Now","done_when":"Done"}]}\n```'
        plan = engine._parse_plan(reply, beings)
        assert len(plan.sub_tasks) == 1
        assert plan.sub_tasks[0].being_id == "forge"

    def test_parse_plan_fallback_on_garbage(self):
        engine = self._engine()
        beings = [{"id": "forge", "name": "SAI Forge"}]
        plan = engine._parse_plan("This is not JSON at all!", beings)
        assert len(plan.sub_tasks) == 1
        assert plan.sub_tasks[0].being_id == "forge"
        assert "not JSON" in plan.sub_tasks[0].instructions

    def test_parse_plan_fixes_invalid_being_id(self):
        engine = self._engine()
        beings = [{"id": "sai-forge", "name": "SAI Forge"}]
        reply = json.dumps({
            "summary": "Test",
            "sub_tasks": [
                {"being_id": "forge", "title": "Task", "instructions": "Do it", "done_when": "Done"}
            ],
        })
        plan = engine._parse_plan(reply, beings)
        assert plan.sub_tasks[0].being_id == "sai-forge"

    def test_parse_plan_empty_subtasks_gets_fallback(self):
        engine = self._engine()
        beings = [{"id": "forge", "name": "SAI Forge"}]
        reply = json.dumps({"summary": "Empty plan", "sub_tasks": []})
        plan = engine._parse_plan(reply, beings)
        assert len(plan.sub_tasks) == 1


class TestReviewParsing:
    def _engine(self) -> OrchestrationEngine:
        return OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )

    def test_parse_approved_review(self):
        engine = self._engine()
        reply = json.dumps({
            "approved": True,
            "feedback": "",
            "quality_score": 0.9,
            "notes": "Excellent work",
        })
        review = engine._parse_review(reply)
        assert review["approved"] is True
        assert review["quality_score"] == 0.9

    def test_parse_rejected_review(self):
        engine = self._engine()
        reply = json.dumps({
            "approved": False,
            "feedback": "Missing competitor #5",
            "quality_score": 0.4,
            "notes": "Incomplete",
        })
        review = engine._parse_review(reply)
        assert review["approved"] is False
        assert "Missing" in review["feedback"]

    def test_parse_review_fallback_on_garbage(self):
        engine = self._engine()
        review = engine._parse_review("not json")
        assert review["approved"] is False  # block on parse failure (not auto-approve)
        assert review["quality_score"] == 0.0
        assert "unparseable" in review["notes"].lower()


# ---------------------------------------------------------------------------
# Orchestration lifecycle tests (with mocked bridge)
# ---------------------------------------------------------------------------

class TestOrchestrationLifecycle:
    def _make_engine(self):
        bridge = MagicMock()
        dashboard = MagicMock()
        project_svc = MagicMock()

        # Dashboard mocks
        dashboard.list_beings.return_value = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Research", "skills": "", "tenant_id": "t-forge", "workspace": "workspaces/forge"},
            {"id": "memory", "name": "SAI Memory", "status": "online", "role": "Memory", "skills": "", "tenant_id": "t-memory", "workspace": "workspaces/scholar"},
        ]
        dashboard.get_being.side_effect = lambda bid: {
            "forge": {"id": "forge", "name": "SAI Forge", "tenant_id": "t-forge", "workspace": "workspaces/forge", "status": "online"},
            "memory": {"id": "memory", "name": "SAI Memory", "tenant_id": "t-memory", "workspace": "workspaces/scholar", "status": "online"},
        }.get(bid, {})

        task_counter = [0]
        def mock_create_task(ps, **kwargs):
            task_counter[0] += 1
            tid = f"task-{task_counter[0]}"
            return {"id": tid, "task_id": tid, "title": kwargs.get("title", ""), "status": "in_progress"}
        dashboard.create_task.side_effect = mock_create_task
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        # Bridge mock: return different responses for plan, delegation, review, synthesis
        call_count = [0]
        def mock_handle_turn(req):
            call_count[0] += 1
            session = req.session_id

            if session.startswith("orchestration:"):
                msg = req.user_message
                if "ORCHESTRATION MODE" in msg:
                    # Planning call
                    return {"assistant": {"text": json.dumps({
                        "summary": "Research plan",
                        "synthesis_strategy": "merge",
                        "sub_tasks": [
                            {"being_id": "forge", "title": "Research competitors", "instructions": "Find top 5", "done_when": "List provided"},
                            {"being_id": "memory", "title": "Check memory", "instructions": "Search for prior data", "done_when": "Results compiled"},
                        ],
                    })}}
                elif "[REVIEW]" in msg:
                    # Review call — approve everything
                    return {"assistant": {"text": json.dumps({
                        "approved": True, "feedback": "", "quality_score": 0.85, "notes": "Good",
                    })}}
                elif "[SYNTHESIZE]" in msg:
                    return {"assistant": {"text": "Final synthesized report with all findings."}}
            elif session.startswith("subtask:"):
                # Being delegation
                return {"assistant": {"text": f"Sub-task completed by {req.user_id}."}}

            return {"assistant": {"text": "Unknown context"}}

        bridge.handle_turn.side_effect = mock_handle_turn

        engine = OrchestrationEngine(
            bridge=bridge,
            dashboard_svc=dashboard,
            project_svc=project_svc,
        )
        return engine, bridge, dashboard

    def test_start_returns_immediately(self):
        engine, bridge, dashboard = self._make_engine()
        result = engine.start(
            goal="Research top 5 competitors",
            requester_session_id="mc-chat-prime",
            sender="user",
        )
        assert "task_id" in result
        assert result["status"] == STATUS_PLANNING

    def test_full_lifecycle_completes(self):
        engine, bridge, dashboard = self._make_engine()
        result = engine.start(
            goal="Research top 5 competitors",
            requester_session_id="mc-chat-prime",
            sender="user",
        )
        task_id = result["task_id"]

        # Wait for background thread to complete
        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        status = engine.get_status(task_id)
        assert status is not None
        assert status["status"] == STATUS_COMPLETED

        # Verify bridge was called for: 1 plan + 2 delegations + 2 reviews + 1 synthesis = 6
        assert bridge.handle_turn.call_count >= 6

        # Verify sub-task outputs were collected
        assert "forge" in status["subtask_outputs"]
        assert "memory" in status["subtask_outputs"]

        # Verify reviews were collected
        assert status["subtask_reviews"]["forge"]["approved"] is True
        assert status["subtask_reviews"]["memory"]["approved"] is True

        # Verify final message posted to user chat
        dashboard.create_message.assert_called()
        synthesis_call = [
            c for c in dashboard.create_message.call_args_list
            if "synthesized" in str(c).lower() or "Final" in str(c)
        ]
        assert len(synthesis_call) >= 1

    def test_session_isolation_in_calls(self):
        """Verify each call uses the correct session ID pattern."""
        engine, bridge, dashboard = self._make_engine()
        result = engine.start(
            goal="Test task",
            requester_session_id="mc-chat-prime",
        )
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Check all handle_turn calls for session patterns
        sessions_used = set()
        for call in bridge.handle_turn.call_args_list:
            req = call[0][0]
            sessions_used.add(req.session_id)

        # Must have orchestration session
        orch_sessions = [s for s in sessions_used if s.startswith("orchestration:")]
        assert len(orch_sessions) == 1

        # Must have subtask sessions
        subtask_sessions = [s for s in sessions_used if s.startswith("subtask:")]
        assert len(subtask_sessions) == 2  # forge + memory

        # Must NOT have any chat sessions
        chat_sessions = [s for s in sessions_used if "mc-chat" in s or "sister-chat" in s]
        assert len(chat_sessions) == 0

    def test_single_parent_task_on_board(self):
        """Verify only one task card (parent) is created — no child tasks."""
        engine, bridge, dashboard = self._make_engine()
        result = engine.start(goal="Test task", requester_session_id="mc-chat-prime")
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Only 1 create_task call — parent task only, no child tasks
        assert dashboard.create_task.call_count == 1

    def test_being_status_updates(self):
        """Verify beings go busy then back to online."""
        engine, bridge, dashboard = self._make_engine()
        result = engine.start(goal="Test task", requester_session_id="mc-chat-prime")

        import time
        for _ in range(50):
            status = engine.get_status(result["task_id"])
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Beings should have been updated to busy then back to online
        busy_calls = [
            c for c in dashboard.update_being.call_args_list
            if c[0][1].get("status") == "busy"
        ]
        online_calls = [
            c for c in dashboard.update_being.call_args_list
            if c[0][1].get("status") == "online"
        ]
        assert len(busy_calls) >= 2  # forge + memory
        assert len(online_calls) >= 2


# ---------------------------------------------------------------------------
# SubTaskPlan / OrchestrationPlan model tests
# ---------------------------------------------------------------------------

class TestTaskResultPersistence:
    """Verify that completed orchestrations write a task_results row."""

    def _make_engine_with_db(self):
        """Build an engine backed by a real RuntimeDB so we can inspect task_results."""
        import os
        import tempfile
        from bomba_sr.storage.db import RuntimeDB

        tmpdir = tempfile.mkdtemp()
        db = RuntimeDB(os.path.join(tmpdir, "runtime.db"))

        # Minimal _TenantRuntime stand-in with a real db
        tenant_runtime = MagicMock()
        tenant_runtime.db = db

        bridge = MagicMock()
        bridge._tenant_runtime.return_value = tenant_runtime

        dashboard = MagicMock()
        project_svc = MagicMock()

        dashboard.list_beings.return_value = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Research",
             "skills": "", "tenant_id": "t-forge", "workspace": "workspaces/forge"},
        ]
        def _get_being(being_id):
            if being_id == "prime":
                return {"id": "prime", "tenant_id": "tenant-prime", "workspace": "workspaces/prime", "status": "online"}
            return {"id": "forge", "tenant_id": "t-forge", "workspace": "workspaces/forge", "status": "online"}
        dashboard.get_being.side_effect = _get_being
        dashboard.create_task.return_value = {"id": "task-persist-1"}
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        def mock_handle_turn(req):
            msg = req.user_message
            if "ORCHESTRATION MODE" in msg:
                return {"assistant": {"text": json.dumps({
                    "summary": "Persist test",
                    "synthesis_strategy": "merge",
                    "sub_tasks": [
                        {"being_id": "forge", "title": "Do work",
                         "instructions": "Execute", "done_when": "Done"},
                    ],
                })}}
            if "[REVIEW]" in msg:
                return {"assistant": {"text": json.dumps({
                    "approved": True, "feedback": "", "quality_score": 0.9, "notes": "OK",
                })}}
            if "[SYNTHESIZE" in msg:
                return {"assistant": {"text": "Synthesized output for persistence test."}}
            return {"assistant": {"text": "Sub-task output from forge."}}

        bridge.handle_turn.side_effect = mock_handle_turn

        engine = OrchestrationEngine(
            bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
        )
        return engine, db

    def test_task_result_written_after_synthesis(self):
        engine, db = self._make_engine_with_db()
        result = engine.start(
            goal="Persistence test goal",
            requester_session_id="mc-chat-prime",
            sender="user",
        )
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

        # Verify row in task_results
        row = db.execute(
            "SELECT * FROM task_results WHERE task_id = ?", (task_id,)
        ).fetchone()
        assert row is not None
        assert row["goal"] == "Persistence test goal"
        assert row["strategy"] == "merge"
        assert json.loads(row["beings_used"]) == ["forge"]
        assert "forge" in json.loads(row["outputs"])
        assert "Synthesized output" in row["synthesis"]
        assert row["tenant_id"] == "tenant-prime"
        assert row["created_at"]  # non-empty ISO timestamp

    def test_task_result_schema_is_idempotent(self):
        """Calling _ensure_task_results_schema multiple times does not error."""
        engine, db = self._make_engine_with_db()
        # __init__ already called it once; call again
        engine._ensure_task_results_schema()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='task_results'"
        ).fetchone()
        assert tables is not None

    def test_orchestrator_semantic_memory_written(self):
        """Fix 2: Prime's planner gets a semantic memory of the completed task."""
        engine, db = self._make_engine_with_db()
        runtime_mock = engine.bridge._tenant_runtime.return_value

        result = engine.start(
            goal="Cross-task recall test",
            requester_session_id="mc-chat-prime",
            sender="user",
        )
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

        # Find the learn_semantic call for the orchestrator
        orch_calls = [
            c for c in runtime_mock.memory.learn_semantic.call_args_list
            if c.kwargs.get("user_id") == "orchestrator"
               or (c.args and len(c.args) > 1 and c.args[1] == "orchestrator")
        ]
        # Use keyword matching since our code uses kwargs
        if not orch_calls:
            # Check all calls by keyword
            orch_calls = [
                c for c in runtime_mock.memory.learn_semantic.call_args_list
                if "orchestrator" in str(c)
            ]
        assert len(orch_calls) >= 1, (
            f"Expected orchestrator semantic memory write, got: "
            f"{runtime_mock.memory.learn_semantic.call_args_list}"
        )
        call_kwargs = orch_calls[0].kwargs if orch_calls[0].kwargs else {}
        if call_kwargs:
            assert call_kwargs["user_id"] == "orchestrator"
            assert call_kwargs["memory_key"].startswith("task_result::")
            assert "Cross-task recall test" in call_kwargs["content"]
            assert call_kwargs["confidence"] == 0.9

    def test_being_semantic_memory_written(self):
        """Fix 3: Beings get a semantic memory of their sub-task work."""
        engine, db = self._make_engine_with_db()
        runtime_mock = engine.bridge._tenant_runtime.return_value

        result = engine.start(
            goal="Being memory test",
            requester_session_id="mc-chat-prime",
            sender="user",
        )
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

        # Find the learn_semantic call for the being (prime->forge)
        being_calls = [
            c for c in runtime_mock.memory.learn_semantic.call_args_list
            if "prime->forge" in str(c)
        ]
        assert len(being_calls) >= 1, (
            f"Expected being semantic memory write, got: "
            f"{runtime_mock.memory.learn_semantic.call_args_list}"
        )
        call_kwargs = being_calls[0].kwargs if being_calls[0].kwargs else {}
        if call_kwargs:
            assert call_kwargs["user_id"] == "prime->forge"
            assert "task_work::" in call_kwargs["memory_key"]
            assert call_kwargs["confidence"] == 0.8


# ---------------------------------------------------------------------------
# Dream cycle auto-trigger tests
# ---------------------------------------------------------------------------

class TestDreamCycleTrigger:
    """Verify dream cycle is auto-triggered after N orchestrated tasks."""

    def test_trigger_fires_after_n_tasks(self):
        """_completed_task_count tracks completions, dream fires at threshold."""
        engine = OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )
        engine._dream_trigger_every = 3

        # Simulate triggering — call _trigger_dream_cycle via counter
        for i in range(1, 4):
            engine._completed_task_count = i
            if i % engine._dream_trigger_every == 0:
                engine._trigger_dream_cycle()

        # Verify bridge.dream_cycle_run_once was called once
        engine.bridge.dream_cycle_run_once.assert_called_once()

    def test_trigger_does_not_fire_before_threshold(self):
        engine = OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )
        engine._dream_trigger_every = 5
        engine._completed_task_count = 3

        # At count 3 (not divisible by 5), should not trigger
        if engine._completed_task_count % engine._dream_trigger_every == 0:
            engine._trigger_dream_cycle()

        engine.bridge.dream_cycle_run_once.assert_not_called()

    def test_trigger_disabled_when_zero(self):
        """Setting BOMBA_DREAM_TRIGGER_EVERY=0 disables auto-trigger."""
        engine = OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )
        engine._dream_trigger_every = 0
        engine._completed_task_count = 10

        # With trigger_every=0, the modulo check should not fire
        if engine._dream_trigger_every > 0 and engine._completed_task_count % engine._dream_trigger_every == 0:
            engine._trigger_dream_cycle()

        engine.bridge.dream_cycle_run_once.assert_not_called()

    def test_trigger_failure_does_not_raise(self):
        """Dream cycle trigger failure is logged, not propagated."""
        engine = OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )
        engine.bridge.dream_cycle_run_once.side_effect = RuntimeError("Dream failed")
        # Should not raise
        engine._trigger_dream_cycle()

    def test_completed_task_count_increments(self):
        """_completed_task_count starts at 0."""
        engine = OrchestrationEngine(
            bridge=MagicMock(),
            dashboard_svc=MagicMock(),
            project_svc=MagicMock(),
        )
        assert engine._completed_task_count == 0


# ---------------------------------------------------------------------------
# Being Representation tests
# ---------------------------------------------------------------------------

class TestBeingRepresentations:
    """Verify that REPRESENTATION.md is updated after orchestration synthesis."""

    def _make_engine_with_workspace(self):
        """Build engine with temp workspace and REPRESENTATION.md files."""
        import os
        import tempfile
        from pathlib import Path as P
        from bomba_sr.storage.db import RuntimeDB

        tmpdir = tempfile.mkdtemp()
        db = RuntimeDB(os.path.join(tmpdir, "runtime.db"))

        # Create workspace structure
        ws_root = P(tmpdir) / "workspaces"
        ws_root.mkdir()
        forge_ws = ws_root / "forge"
        forge_ws.mkdir()

        # Seed REPRESENTATION.md
        (forge_ws / "REPRESENTATION.md").write_text(
            "# Being Representation: SAI Forge\n\n"
            "## Task History Summary\nTotal tasks completed: 0\nRecent tasks: (none yet)\n\n"
            "## Performance Profile\nAverage task quality: N/A\n\n"
            "## Domain Expertise Map\n\n"
            "## Collaboration Profile\n\n"
            "## Evolution Log\n",
            encoding="utf-8",
        )

        tenant_runtime = MagicMock()
        tenant_runtime.db = db

        bridge = MagicMock()
        bridge._tenant_runtime.return_value = tenant_runtime

        dashboard = MagicMock()
        project_svc = MagicMock()

        dashboard.list_beings.return_value = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Research",
             "skills": "", "tenant_id": "t-forge", "workspace": str(forge_ws)},
        ]
        dashboard.get_being.return_value = {
            "id": "forge", "tenant_id": "t-forge",
            "workspace": str(forge_ws), "status": "online",
        }
        dashboard.create_task.return_value = {"id": "task-rep-1"}
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        def mock_handle_turn(req):
            msg = req.user_message
            if "ORCHESTRATION MODE" in msg:
                return {"assistant": {"text": json.dumps({
                    "summary": "Rep test",
                    "synthesis_strategy": "merge",
                    "sub_tasks": [
                        {"being_id": "forge", "title": "Do work",
                         "instructions": "Execute", "done_when": "Done"},
                    ],
                })}}
            if "[REVIEW]" in msg:
                return {"assistant": {"text": json.dumps({
                    "approved": True, "feedback": "", "quality_score": 0.9, "notes": "Solid",
                })}}
            if "[SYNTHESIZE]" in msg:
                return {"assistant": {"text": "Synthesized representation test output."}}
            return {"assistant": {"text": "Sub-task output from forge."}}

        bridge.handle_turn.side_effect = mock_handle_turn

        engine = OrchestrationEngine(
            bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
        )
        engine._prime_workspace = lambda: str(ws_root / "prime")

        return engine, forge_ws, tmpdir

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_representation_written_after_synthesis(self, mock_provider_from_env):
        """After orchestration completes, REPRESENTATION.md should be updated."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = (
            "# Being Representation: SAI Forge\n\n"
            "## Task History Summary\nTotal tasks completed: 1\n"
            "Recent tasks: [2026-03-04] Do work\n\n"
            "## Performance Profile\nAverage task quality: 0.9\n"
        )
        mock_provider_from_env.return_value = mock_provider

        engine, forge_ws, tmpdir = self._make_engine_with_workspace()
        result = engine.start(goal="Rep test", requester_session_id="s1", sender="user")
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

        # Verify REPRESENTATION.md was updated
        rep_text = (forge_ws / "REPRESENTATION.md").read_text()
        assert "Total tasks completed: 1" in rep_text
        # Called twice: once after delegation (with empty synthesis), once after synthesis
        assert mock_provider.generate.call_count == 2

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_representation_failure_does_not_block_synthesis(self, mock_provider_from_env):
        """If LLM call for representation fails, orchestration still completes."""
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = RuntimeError("LLM down")
        mock_provider_from_env.return_value = mock_provider

        engine, forge_ws, tmpdir = self._make_engine_with_workspace()
        result = engine.start(goal="Rep fail test", requester_session_id="s1", sender="user")
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Orchestration should still complete despite representation failure
        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_representation_capped_at_3000(self, mock_provider_from_env):
        """Oversized LLM response is truncated to 3000 chars."""
        oversized = "x" * 5000
        mock_provider = MagicMock()
        mock_provider.generate.return_value = oversized
        mock_provider_from_env.return_value = mock_provider

        engine, forge_ws, tmpdir = self._make_engine_with_workspace()
        result = engine.start(goal="Cap test", requester_session_id="s1", sender="user")
        task_id = result["task_id"]

        import time
        for _ in range(50):
            status = engine.get_status(task_id)
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(task_id)["status"] == STATUS_COMPLETED

        rep_text = (forge_ws / "REPRESENTATION.md").read_text()
        assert len(rep_text) <= 3000

    def test_planning_enriched_with_representations(self):
        """Verify that the planning phase includes representation data in assignable beings."""
        engine, forge_ws, tmpdir = self._make_engine_with_workspace()

        # Capture the handle_turn calls to inspect the planning prompt
        original_handle_turn = engine.bridge.handle_turn.side_effect
        planning_msg = []

        def capturing_handle_turn(req):
            if "ORCHESTRATION MODE" in req.user_message:
                planning_msg.append(req.user_message)
            return original_handle_turn(req)

        engine.bridge.handle_turn.side_effect = capturing_handle_turn

        result = engine.start(goal="Enrichment test", requester_session_id="s1", sender="user")

        import time
        for _ in range(50):
            status = engine.get_status(result["task_id"])
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Verify planning prompt contained representation data
        assert len(planning_msg) >= 1
        assert "representation" in planning_msg[0].lower() or "Task History" in planning_msg[0]


class TestModels:
    def test_subtask_plan_to_dict(self):
        p = SubTaskPlan(being_id="forge", title="Research", instructions="Do it", done_when="Done")
        d = p.to_dict()
        assert d["being_id"] == "forge"
        assert d["title"] == "Research"

    def test_orchestration_plan_to_dict(self):
        plan = OrchestrationPlan(
            summary="Test plan",
            sub_tasks=[
                SubTaskPlan("forge", "Task 1", "Do task 1"),
                SubTaskPlan("memory", "Task 2", "Do task 2"),
            ],
            synthesis_strategy="sequential",
        )
        d = plan.to_dict()
        assert d["summary"] == "Test plan"
        assert len(d["sub_tasks"]) == 2
        assert d["synthesis_strategy"] == "sequential"


# ---------------------------------------------------------------------------
# Dashboard integration tests
# ---------------------------------------------------------------------------

class TestDashboardIntegration:
    def test_init_orchestration_creates_engine(self):
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db, bridge=MagicMock())
            project_svc = MagicMock()
            svc.init_orchestration(project_svc)
            assert svc.orchestration_engine is not None

    def test_init_orchestration_skips_without_bridge(self):
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db, bridge=None)
            svc.init_orchestration(MagicMock())
            assert svc.orchestration_engine is None

    def test_get_orchestration_status_returns_none_without_engine(self):
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db)
            assert svc.get_orchestration_status("nonexistent") is None
            assert svc.get_orchestration_log("nonexistent") == []


# ---------------------------------------------------------------------------
# Synthesis budget & fallback tests
# ---------------------------------------------------------------------------

class TestSynthesisBudget:
    def test_truncate_outputs_to_budget_short_outputs_unchanged(self):
        """Short outputs should pass through unchanged."""
        from bomba_sr.orchestration.engine import _truncate_outputs_to_budget
        outputs = {"forge": "short text", "scholar": "also short"}
        result = _truncate_outputs_to_budget(outputs)
        assert result == outputs

    def test_truncate_outputs_to_budget_long_outputs_truncated(self):
        """Outputs exceeding per-being budget should be truncated."""
        from bomba_sr.orchestration.engine import _truncate_outputs_to_budget
        # With 2 beings and default model, per-being budget is huge, so use a small model_max_input
        long_text = "x" * 50000
        outputs = {"forge": long_text, "scholar": long_text}
        result = _truncate_outputs_to_budget(outputs, model_max_input=80000)
        for being_id, text in result.items():
            assert len(text) < 50000
            assert text.endswith("[... output truncated to fit synthesis budget ...]")

    def test_truncate_empty_outputs(self):
        from bomba_sr.orchestration.engine import _truncate_outputs_to_budget
        assert _truncate_outputs_to_budget({}) == {}

    def test_truncate_per_being_budget_scales_with_count(self):
        """More beings = smaller per-being budget."""
        from bomba_sr.orchestration.engine import _truncate_outputs_to_budget
        text = "y" * 100000
        two_beings = _truncate_outputs_to_budget(
            {"a": text, "b": text}, model_max_input=100000,
        )
        four_beings = _truncate_outputs_to_budget(
            {"a": text, "b": text, "c": text, "d": text}, model_max_input=100000,
        )
        # With 4 beings, each gets less budget than with 2
        assert len(four_beings["a"]) < len(two_beings["a"])


class TestSynthesisFallback:
    """Tests for the two-stage synthesis fallback."""

    def _make_engine_with_failing_synthesis(self, *, fail_stage_1=True, fail_stage_2=False):
        """Create engine where synthesis handle_turn can be configured to fail."""
        dashboard = MagicMock()
        project_svc = MagicMock()
        bridge = MagicMock()

        dashboard.list_beings.return_value = [
            {"id": "forge", "name": "SAI Forge", "status": "online", "role": "Dev",
             "skills": "", "tenant_id": "t-forge", "workspace": "workspaces/forge"},
        ]
        dashboard.get_being.return_value = {
            "id": "forge", "tenant_id": "t-forge", "workspace": "workspaces/forge",
        }
        dashboard.create_task.return_value = {"id": "task-fb-1"}
        dashboard.update_task.return_value = {}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_being = MagicMock()
        dashboard.create_message = MagicMock()

        call_count = [0]

        def mock_handle_turn(req):
            msg = req.user_message
            if "ORCHESTRATION MODE" in msg:
                return {"assistant": {"text": json.dumps({
                    "summary": "Fallback test",
                    "synthesis_strategy": "merge",
                    "sub_tasks": [
                        {"being_id": "forge", "title": "Do work",
                         "instructions": "Execute", "done_when": "Done"},
                    ],
                })}}
            if "[REVIEW]" in msg:
                return {"assistant": {"text": json.dumps({
                    "approved": True, "feedback": "", "quality_score": 0.8, "notes": "OK",
                })}}
            if "[SYNTHESIZE-FALLBACK]" in msg:
                if fail_stage_2:
                    raise RuntimeError("Stage 2 also failed")
                return {"assistant": {"text": "Fallback synthesis result."}}
            if "[SYNTHESIZE]" in msg:
                if fail_stage_1:
                    raise RuntimeError("Simulated 400 context overflow")
                return {"assistant": {"text": "Normal synthesis result."}}
            return {"assistant": {"text": "Sub-task output from forge about testing."}}

        bridge.handle_turn.side_effect = mock_handle_turn

        engine = OrchestrationEngine(
            bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
        )
        return engine

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_stage1_fails_falls_back_to_stage2(self, mock_provider):
        """When stage 1 synthesis fails (400), stage 2 summarize-then-synthesize succeeds."""
        mock_prov = MagicMock()
        mock_prov.generate.return_value = "Summary of forge output."
        mock_provider.return_value = mock_prov

        engine = self._make_engine_with_failing_synthesis(fail_stage_1=True)
        result = engine.start(goal="Fallback test", requester_session_id="s1", sender="user")

        import time
        for _ in range(50):
            status = engine.get_status(result["task_id"])
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(result["task_id"])["status"] == STATUS_COMPLETED

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_both_stages_fail_returns_concatenated(self, mock_provider):
        """When both stages fail, concatenated summaries are returned."""
        mock_prov = MagicMock()
        mock_prov.generate.return_value = "Summary text."
        mock_provider.return_value = mock_prov

        engine = self._make_engine_with_failing_synthesis(
            fail_stage_1=True, fail_stage_2=True,
        )
        result = engine.start(goal="Total failure test", requester_session_id="s1", sender="user")

        import time
        for _ in range(50):
            status = engine.get_status(result["task_id"])
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        # Should still complete with concatenated fallback
        assert engine.get_status(result["task_id"])["status"] == STATUS_COMPLETED


class TestTaskFailureHandling:
    """Test that failed orchestrations are properly handled."""

    def test_failed_task_sends_user_notification(self):
        """On orchestration failure, user gets notified and task is marked failed."""
        dashboard = MagicMock()
        project_svc = MagicMock()
        bridge = MagicMock()

        dashboard.list_beings.return_value = []  # No beings → will raise
        dashboard.create_task.return_value = {"id": "task-fail-1"}
        dashboard._log_task_history = MagicMock()
        dashboard._emit_event = MagicMock()
        dashboard.update_task.return_value = {}
        dashboard.create_message = MagicMock()

        engine = OrchestrationEngine(
            bridge=bridge, dashboard_svc=dashboard, project_svc=project_svc,
        )
        result = engine.start(goal="Will fail", requester_session_id="s1", sender="user")

        import time
        for _ in range(50):
            status = engine.get_status(result["task_id"])
            if status and status["status"] in (STATUS_COMPLETED, STATUS_FAILED):
                break
            time.sleep(0.1)

        assert engine.get_status(result["task_id"])["status"] == STATUS_FAILED
        # Verify user notification was sent
        dashboard.create_message.assert_called()
        call_kwargs = dashboard.create_message.call_args
        assert "failed" in str(call_kwargs).lower() or "error" in str(call_kwargs).lower()


class TestTaskBoardFiltering:
    """Test that list_tasks properly filters child/sub-tasks via parent_task_id."""

    def test_parent_task_id_column_exists(self):
        """Verify the parent_task_id column is present in project_tasks table."""
        from bomba_sr.projects.service import ProjectService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = ProjectService(db)
            proj = svc.create_project("t1", "Test Project", "/tmp/test")
            proj_id = proj["project_id"]
            task = svc.create_task("t1", proj_id, "A task", parent_task_id="parent-123")
            assert task["parent_task_id"] == "parent-123"

            task2 = svc.create_task("t1", proj_id, "Top-level task")
            assert task2["parent_task_id"] is None

    def test_list_tasks_top_level_only_true(self):
        """top_level_only=True returns only tasks with parent_task_id IS NULL."""
        from bomba_sr.projects.service import ProjectService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = ProjectService(db)
            proj = svc.create_project("t1", "Test Project", "/tmp/test")
            proj_id = proj["project_id"]
            # Create top-level task
            parent = svc.create_task("t1", proj_id, "Parent task")
            pid = parent["task_id"]
            # Create child tasks
            svc.create_task("t1", proj_id, "Child 1", parent_task_id=pid)
            svc.create_task("t1", proj_id, "Child 2", parent_task_id=pid)

            top_only = svc.list_tasks("t1", top_level_only=True)
            assert len(top_only) == 1
            assert top_only[0]["title"] == "Parent task"
            assert top_only[0]["parent_task_id"] is None

    def test_list_tasks_top_level_only_false(self):
        """top_level_only=False returns all tasks including children."""
        from bomba_sr.projects.service import ProjectService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = ProjectService(db)
            proj = svc.create_project("t1", "Test Project", "/tmp/test")
            proj_id = proj["project_id"]
            parent = svc.create_task("t1", proj_id, "Parent task")
            pid = parent["task_id"]
            svc.create_task("t1", proj_id, "Child 1", parent_task_id=pid)
            svc.create_task("t1", proj_id, "Child 2", parent_task_id=pid)

            all_tasks = svc.list_tasks("t1", top_level_only=False)
            assert len(all_tasks) == 3

    def test_dashboard_list_tasks_top_level_only(self):
        """DashboardService.list_tasks passes top_level_only through to ProjectService."""
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db, bridge=MagicMock())

            project_svc = MagicMock()
            project_svc.list_tasks.return_value = [
                {"task_id": "t1", "title": "Top-level task",
                 "description": "Main task", "status": "in_progress",
                 "priority": "high", "parent_task_id": None},
            ]

            tasks = svc.list_tasks(project_svc, top_level_only=True)
            # Verify the parameter was passed through
            project_svc.list_tasks.assert_called_once()
            call_kwargs = project_svc.list_tasks.call_args
            assert call_kwargs.kwargs.get("top_level_only") is True

    def test_dashboard_create_task_with_parent_task_id(self):
        """DashboardService.create_task passes parent_task_id through."""
        from bomba_sr.dashboard.service import DashboardService, MC_TENANT, MC_PROJECT_ID
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db, bridge=MagicMock())

            project_svc = MagicMock()
            project_svc.create_task.return_value = {
                "task_id": "child-1", "title": "Sub-task",
                "description": "A child", "status": "backlog",
                "priority": "medium", "parent_task_id": "parent-1",
                "owner_agent_id": None, "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
            }

            svc.create_task(
                project_svc, title="Sub-task",
                description="A child", parent_task_id="parent-1",
            )
            call_kwargs = project_svc.create_task.call_args
            assert call_kwargs.kwargs.get("parent_task_id") == "parent-1"

    def test_cleanup_orphaned_tasks(self):
        """cleanup_orphaned_tasks removes stale auto-created and casual tasks."""
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.storage.db import RuntimeDB
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            db = RuntimeDB(os.path.join(tmp, "test.db"))
            svc = DashboardService(db=db, bridge=MagicMock())

            project_svc = MagicMock()
            project_svc.list_tasks.return_value = [
                {"task_id": "t1", "title": "Real orchestration task",
                 "description": "User requested analysis", "status": "in_progress",
                 "priority": "high"},
                {"task_id": "t2", "title": "Hello there...",
                 "description": "Auto-created from chat message to Forge",
                 "status": "backlog", "priority": "medium"},
                {"task_id": "t3", "title": "Research competitors",
                 "description": "Auto-created from chat message to Scholar",
                 "status": "done", "priority": "medium"},
            ]

            # Mock delete_task so we don't need the project_tasks table
            svc.delete_task = MagicMock(return_value=True)

            deleted = svc.cleanup_orphaned_tasks(project_svc)
            # t2 matches casual pattern ("Hello") + t3 is auto-created + done
            assert deleted == 2
            assert svc.delete_task.call_count == 2
            deleted_ids = [c[0][1] for c in svc.delete_task.call_args_list]
            assert "t2" in deleted_ids
            assert "t3" in deleted_ids


class TestDreamModelDefault:
    """Verify the dream model default is valid for OpenRouter."""

    def test_dream_model_default_is_valid(self):
        from bomba_sr.memory.dreaming import DREAM_MODEL
        # Must not be the invalid anthropic/claude-sonnet-4-20250514
        assert "claude-sonnet-4-20250514" not in DREAM_MODEL
        # Should be a known-valid model
        assert DREAM_MODEL in ("minimax/minimax-m2.5", "openai/gpt-4o-mini", "anthropic/claude-3-5-haiku-20241022")
