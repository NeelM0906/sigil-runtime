"""Tests for the Mission Control DashboardService."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.dashboard.service import (
    DashboardService, MC_TENANT, MC_PROJECT_ID,
    TYPE_SISTER, TYPE_RUNTIME, TYPE_VOICE_AGENT, TYPE_SUBAGENT,
)
from bomba_sr.projects.service import ProjectService
from bomba_sr.storage.db import RuntimeDB


@pytest.fixture()
def db():
    _db = RuntimeDB(":memory:")
    yield _db
    _db.close()


@pytest.fixture()
def project_svc(db):
    return ProjectService(db)


@pytest.fixture()
def svc(db):
    return DashboardService(db=db, bridge=None, sisters=None)


@pytest.fixture()
def svc_with_bridge(db):
    mock_bridge = MagicMock()
    mock_bridge.handle_turn.return_value = {"reply": "Hello from mock LLM"}
    return DashboardService(db=db, bridge=mock_bridge, sisters=None)


SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "mission-control" / "data"


# ── Schema ────────────────────────────────────────────────────

class TestSchema:
    def test_tables_created(self, db, svc):
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "mc_beings" in tables
        assert "mc_messages" in tables
        assert "mc_task_history" in tables
        assert "mc_task_assignments" in tables
        assert "mc_events" in tables

    def test_idempotent_schema(self, db):
        """Creating the service twice should not fail."""
        DashboardService(db=db)
        DashboardService(db=db)


# ── Beings ────────────────────────────────────────────────────

class TestBeings:
    def test_seed_beings(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        count = svc.seed_beings(path)
        assert count == 7  # 7 beings in seed data
        beings = svc.list_beings()
        assert len(beings) == 7

    def test_seed_idempotent(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        second = svc.seed_beings(path)
        assert second == 0  # no-op

    def test_seed_missing_file(self, svc):
        count = svc.seed_beings("/nonexistent/beings.json")
        assert count == 0

    def test_list_beings_filter_type(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        sisters = svc.list_beings(type_filter="sister")
        assert all(b["type"] == "sister" for b in sisters)
        assert len(sisters) == 3  # forge, scholar, recovery

    def test_list_beings_filter_status(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        online = svc.list_beings(status_filter="online")
        assert all(b["status"] == "online" for b in online)

    def test_get_being(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        b = svc.get_being("prime")
        assert b is not None
        assert b["name"] == "Prime"
        assert b["type"] == "runtime"

    def test_get_being_not_found(self, svc):
        assert svc.get_being("nonexistent") is None

    def test_update_being(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        updated = svc.update_being("prime", {"status": "busy"})
        assert updated["status"] == "busy"

    def test_update_being_not_found(self, svc):
        result = svc.update_being("nonexistent", {"status": "online"})
        assert result is None

    def test_being_tools_deserialized(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        b = svc.get_being("prime")
        assert isinstance(b["tools"], list)
        assert len(b["tools"]) > 0

    def test_sync_being_statuses_no_sisters(self, svc):
        """Should not crash when no sisters registry is available."""
        svc.sync_being_statuses_from_sisters()  # no-op


# ── Config-driven beings loader ──────────────────────────────

class TestConfigLoader:
    def test_load_beings_from_configs(self, svc):
        """Should load beings from real workspace config files."""
        count = svc.load_beings_from_configs()
        assert count > 0
        beings = svc.list_beings()
        assert len(beings) == count

    def test_prime_loaded_as_runtime(self, svc):
        svc.load_beings_from_configs()
        prime = svc.get_being("prime")
        assert prime is not None
        assert prime["type"] == TYPE_RUNTIME
        assert prime["status"] == "online"
        assert prime["workspace"] == "workspaces/prime"

    def test_sisters_loaded_from_json(self, svc):
        svc.load_beings_from_configs()
        forge = svc.get_being("forge")
        assert forge is not None
        assert forge["type"] == TYPE_SISTER
        assert forge["tenant_id"] == "tenant-forge"
        assert forge["workspace"] == "workspaces/forge"

    def test_soul_name_loaded(self, svc):
        """Sisters should get their name from SoulConfig."""
        svc.load_beings_from_configs()
        forge = svc.get_being("forge")
        # SoulConfig parses "Sai Forge" from workspaces/forge/SOUL.md
        assert forge is not None
        assert "Forge" in forge["name"]

    def test_voice_agents_loaded(self, svc):
        svc.load_beings_from_configs()
        callie = svc.get_being("callie")
        assert callie is not None
        assert callie["type"] == TYPE_VOICE_AGENT
        assert callie["agent_id"]  # Should have a Bland agent_id

    def test_voice_agents_no_tenant(self, svc):
        """Voice agents should have no tenant — they live on Bland.ai."""
        svc.load_beings_from_configs()
        callie = svc.get_being("callie")
        assert callie["tenant_id"] == ""

    def test_upsert_idempotent(self, svc):
        """Running load twice should update, not duplicate."""
        count1 = svc.load_beings_from_configs()
        count2 = svc.load_beings_from_configs()
        assert count1 == count2
        beings = svc.list_beings()
        assert len(beings) == count1

    def test_filter_by_type_sister(self, svc):
        svc.load_beings_from_configs()
        sisters = svc.list_beings(type_filter=TYPE_SISTER)
        assert all(b["type"] == TYPE_SISTER for b in sisters)
        assert len(sisters) >= 3  # forge, scholar, recovery at minimum

    def test_filter_by_type_voice(self, svc):
        svc.load_beings_from_configs()
        voice = svc.list_beings(type_filter=TYPE_VOICE_AGENT)
        assert all(b["type"] == TYPE_VOICE_AGENT for b in voice)
        assert len(voice) >= 1

    def test_recovery_sister_tenant(self, svc):
        svc.load_beings_from_configs()
        recovery = svc.get_being("recovery")
        assert recovery is not None
        assert recovery["tenant_id"] == "tenant-recovery"


# ── Chat Messages ─────────────────────────────────────────────

class TestChat:
    def test_create_and_list_messages(self, svc):
        msg = svc.create_message(sender="user", content="Hello world")
        assert msg["sender"] == "user"
        assert msg["content"] == "Hello world"
        assert msg["id"].startswith("msg-")

        msgs = svc.list_messages()
        assert len(msgs) == 1
        assert msgs[0]["id"] == msg["id"]

    def test_message_targets(self, svc):
        msg = svc.create_message(
            sender="user",
            content="@athena check metrics",
            targets=["athena"],
            msg_type="direct",
        )
        assert msg["targets"] == ["athena"]

    def test_filter_by_sender(self, svc):
        svc.create_message(sender="user", content="msg 1")
        svc.create_message(sender="athena", content="msg 2")
        user_msgs = svc.list_messages(sender="user")
        assert len(user_msgs) == 1
        assert user_msgs[0]["sender"] == "user"

    def test_filter_by_search(self, svc):
        svc.create_message(sender="user", content="check metrics please")
        svc.create_message(sender="user", content="hello world")
        results = svc.list_messages(search="metrics")
        assert len(results) == 1

    def test_system_message(self, svc):
        msg = svc.create_system_message("Task created", task_ref="task-001")
        assert msg["type"] == "system"
        assert msg["sender"] == "system"
        assert msg["task_ref"] == "task-001"

    def test_delete_message(self, svc):
        msg = svc.create_message(sender="user", content="to delete")
        assert svc.delete_message(msg["id"]) is True
        assert svc.list_messages() == []

    def test_delete_nonexistent_message(self, svc):
        assert svc.delete_message("msg-nonexistent") is False

    def test_pagination(self, svc):
        for i in range(10):
            svc.create_message(sender="user", content=f"msg {i}")
        page = svc.list_messages(limit=3, offset=0)
        assert len(page) == 3
        page2 = svc.list_messages(limit=3, offset=3)
        assert len(page2) == 3
        assert page[0]["id"] != page2[0]["id"]

    def test_route_to_being_no_bridge(self, svc):
        """Without a bridge, should create an offline placeholder message."""
        svc.route_to_being("athena", "Hello")
        # Wait for the background thread
        time.sleep(0.2)
        msgs = svc.list_messages(sender="athena")
        assert len(msgs) == 1
        assert "offline" in msgs[0]["content"].lower() or "no LLM" in msgs[0]["content"]

    def test_route_to_being_with_bridge(self, svc_with_bridge):
        path = SEED_DATA_DIR / "beings.json"
        if path.exists():
            svc_with_bridge.seed_beings(path)
        svc_with_bridge.route_to_being("athena", "What's our status?")
        time.sleep(0.3)
        msgs = svc_with_bridge.list_messages(sender="athena")
        assert len(msgs) == 1
        assert msgs[0]["content"] == "Hello from mock LLM"

    def test_route_to_voice_agent_rejected(self, svc):
        """Voice agents should not be chat-routable."""
        svc.load_beings_from_configs()
        svc.route_to_being("callie", "Hello")
        time.sleep(0.2)
        msgs = svc.list_messages(sender="callie")
        assert len(msgs) == 1
        assert "voice agent" in msgs[0]["content"].lower()


# ── Tasks ─────────────────────────────────────────────────────

class TestTasks:
    def test_ensure_mc_project(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        proj = project_svc.get_project(MC_TENANT, MC_PROJECT_ID)
        assert proj["name"] == "Mission Control"

    def test_ensure_mc_project_idempotent(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.ensure_mc_project(project_svc)  # should not fail

    def test_create_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Test task", priority="high")
        assert task["title"] == "Test task"
        assert task["priority"] == "high"
        assert task["status"] == "backlog"
        assert "assignees" in task

    def test_create_task_with_assignees(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(
            project_svc, title="Assigned task",
            assignees=["athena", "callie"],
        )
        assert set(task["assignees"]) == {"athena", "callie"}

    def test_list_tasks(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="Task A")
        svc.create_task(project_svc, title="Task B", priority="high")
        tasks = svc.list_tasks(project_svc)
        assert len(tasks) == 2

    def test_list_tasks_filter_priority(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="Normal", priority="normal")
        svc.create_task(project_svc, title="High", priority="high")
        high = svc.list_tasks(project_svc, priority="high")
        assert len(high) == 1
        assert high[0]["priority"] == "high"

    def test_list_tasks_filter_assignee(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="For Athena", assignees=["athena"])
        svc.create_task(project_svc, title="For Callie", assignees=["callie"])
        athena_tasks = svc.list_tasks(project_svc, assignee="athena")
        assert len(athena_tasks) == 1

    def test_get_task_with_history(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Task with history")
        result = svc.get_task(project_svc, task["task_id"])
        assert "history" in result
        assert len(result["history"]) >= 1
        assert result["history"][0]["action"] == "created"

    def test_update_task_status(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="To update")
        updated = svc.update_task(project_svc, task["task_id"], status="in_progress")
        assert updated["status"] == "in_progress"

    def test_update_task_assignees(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Reassign", assignees=["athena"])
        updated = svc.update_task(
            project_svc, task["task_id"],
            assignees=["callie", "mylo"],
        )
        assert set(updated["assignees"]) == {"callie", "mylo"}

    def test_delete_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="To delete")
        assert svc.delete_task(project_svc, task["task_id"]) is True
        assert svc.list_tasks(project_svc) == []

    def test_delete_task_not_found(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        assert svc.delete_task(project_svc, "nonexistent") is False

    def test_task_history_global(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="A")
        svc.create_task(project_svc, title="B")
        history = svc.task_history()
        assert len(history) == 2

    def test_task_history_per_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Tracked")
        svc.update_task(project_svc, task["task_id"], status="in_progress")
        history = svc.task_history(task_id=task["task_id"])
        assert len(history) == 2  # created + updated


# ── SSE ───────────────────────────────────────────────────────

class TestSSE:
    def test_subscribe_unsubscribe(self, svc):
        cid = svc.subscribe_sse()
        assert cid in svc._sse_clients
        svc.unsubscribe_sse(cid)
        assert cid not in svc._sse_clients

    def test_emit_event_delivered(self, svc):
        cid = svc.subscribe_sse()
        svc._emit_event("test_event", {"key": "value"})
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "test_event"
        assert evt["data"]["key"] == "value"
        svc.unsubscribe_sse(cid)

    def test_emit_event_persisted(self, svc):
        svc._emit_event("test_event", {"key": "value"})
        rows = svc.db.execute("SELECT * FROM mc_events").fetchall()
        assert len(rows) == 1
        assert rows[0]["event_type"] == "test_event"

    def test_poll_timeout(self, svc):
        cid = svc.subscribe_sse()
        evt = svc.poll_sse(cid, timeout=0.1)
        assert evt is None
        svc.unsubscribe_sse(cid)

    def test_chat_message_emits_sse(self, svc):
        cid = svc.subscribe_sse()
        svc.create_message(sender="user", content="SSE test")
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "chat_message"
        assert evt["data"]["content"] == "SSE test"
        svc.unsubscribe_sse(cid)

    def test_being_status_emits_sse(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        cid = svc.subscribe_sse()
        svc.update_being("prime", {"status": "busy"})
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "being_status"
        assert evt["data"]["being_id"] == "prime"
        svc.unsubscribe_sse(cid)

    def test_task_update_emits_sse(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        cid = svc.subscribe_sse()
        svc.create_task(project_svc, title="SSE task")
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "task_update"
        assert evt["data"]["action"] == "created"
        svc.unsubscribe_sse(cid)

    def test_multiple_subscribers(self, svc):
        cid1 = svc.subscribe_sse()
        cid2 = svc.subscribe_sse()
        svc._emit_event("broadcast", {"msg": "hello"})
        e1 = svc.poll_sse(cid1, timeout=1.0)
        e2 = svc.poll_sse(cid2, timeout=1.0)
        assert e1 is not None
        assert e2 is not None
        assert e1["data"]["msg"] == "hello"
        assert e2["data"]["msg"] == "hello"
        svc.unsubscribe_sse(cid1)
        svc.unsubscribe_sse(cid2)


# ── Sub-agents ────────────────────────────────────────────────

class TestSubAgents:
    def test_list_subagent_runs_empty(self, svc):
        runs = svc.list_subagent_runs()
        assert runs == []

    def test_list_subagent_runs_no_table(self, db):
        """Should not crash if subagent_runs table does not exist."""
        svc = DashboardService(db=db)
        runs = svc.list_subagent_runs()
        assert runs == []
