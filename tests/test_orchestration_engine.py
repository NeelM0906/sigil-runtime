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
        assert review["approved"] is True  # auto-approve on parse failure
        assert review["quality_score"] == 0.6


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
        dashboard.get_being.return_value = {
            "id": "forge", "tenant_id": "t-forge", "workspace": "workspaces/forge", "status": "online",
        }
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
            if "[SYNTHESIZE]" in msg:
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
