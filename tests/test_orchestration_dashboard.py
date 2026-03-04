"""Tests for orchestration dashboard integration.

Verifies:
  - Parent/child task relationships via task history
  - Enriched task view with orchestration data
  - Being status detail computation
  - API endpoint routing
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from unittest.mock import MagicMock

import pytest

from bomba_sr.dashboard.service import DashboardService
from bomba_sr.projects.service import ProjectService
from bomba_sr.storage.db import RuntimeDB


@pytest.fixture
def svc():
    with tempfile.TemporaryDirectory() as tmp:
        db = RuntimeDB(os.path.join(tmp, "test.db"))
        dashboard = DashboardService(db=db, bridge=MagicMock())
        project_svc = ProjectService(db)
        project_svc.create_project(
            tenant_id="tenant-local",
            project_id="mc-project",
            name="Mission Control",
            workspace_root="/tmp/test",
        )
        dashboard.project_service = project_svc
        yield dashboard, project_svc, db


class TestParentChildTasks:
    def test_get_task_children_empty(self, svc):
        dashboard, project_svc, _ = svc
        assert dashboard.get_task_children("nonexistent") == []

    def test_get_task_parent_none(self, svc):
        dashboard, project_svc, _ = svc
        assert dashboard.get_task_parent("nonexistent") is None

    def test_parent_child_roundtrip(self, svc):
        dashboard, project_svc, _ = svc

        # Create parent task
        parent = dashboard.create_task(
            project_svc, title="Parent task", status="in_progress",
        )
        parent_id = parent["id"]

        # Create child task with parent_task_id
        child = dashboard.create_task(
            project_svc, title="Child task", status="in_progress",
            assignees=["forge"],
            parent_task_id=parent_id,
        )
        child_id = child["id"]

        # Verify relationships via parent_task_id column
        children = dashboard.get_task_children(parent_id)
        assert children == [child_id]

        parent_of_child = dashboard.get_task_parent(child_id)
        assert parent_of_child == parent_id

    def test_multiple_children(self, svc):
        dashboard, project_svc, _ = svc

        parent = dashboard.create_task(project_svc, title="Parent")
        pid = parent["id"]

        child_ids = []
        for i in range(3):
            child = dashboard.create_task(
                project_svc, title=f"Child {i}",
                assignees=[f"being-{i}"],
                parent_task_id=pid,
            )
            cid = child["id"]
            child_ids.append(cid)

        result = dashboard.get_task_children(pid)
        assert result == child_ids

    def test_get_task_with_orchestration(self, svc):
        dashboard, project_svc, _ = svc

        parent = dashboard.create_task(
            project_svc, title="Orchestrated task", status="in_progress",
        )
        pid = parent["id"]

        child = dashboard.create_task(
            project_svc, title="Sub-task 1", status="done",
            parent_task_id=pid,
        )
        cid = child["id"]

        enriched = dashboard.get_task_with_orchestration(project_svc, pid)
        assert enriched["parent_task_id"] is None  # parent has no parent
        assert len(enriched["children"]) == 1
        assert enriched["children"][0]["id"] == cid


class TestBeingStatusDetail:
    def test_offline_status(self, svc):
        dashboard, _, _ = svc
        being = {"id": "test", "status": "offline"}
        assert dashboard._compute_status_detail(being) == "offline"

    def test_online_no_task(self, svc):
        dashboard, _, _ = svc
        being = {"id": "test", "status": "online", "active_task": None}
        assert dashboard._compute_status_detail(being) == "online"

    def test_busy_chat(self, svc):
        dashboard, _, _ = svc
        being = {"id": "test", "status": "busy", "active_task": None}
        assert dashboard._compute_status_detail(being) == "busy (chat)"

    def test_busy_with_task(self, svc):
        dashboard, _, _ = svc
        being = {
            "id": "test",
            "status": "busy",
            "active_task": {"task_id": "t1", "title": "Research competitors", "status": "in_progress"},
        }
        result = dashboard._compute_status_detail(being)
        assert result.startswith("busy (task:")
        assert "Research competitors" in result

    def test_prime_orchestrating(self, svc):
        dashboard, project_svc, _ = svc
        dashboard.init_orchestration(project_svc)
        # Inject fake active orchestration
        dashboard.orchestration_engine._active["fake-task"] = {
            "status": "delegating",
            "goal": "Research report on medical billing",
        }
        being = {"id": "prime", "status": "busy", "active_task": None}
        result = dashboard._compute_status_detail(being)
        assert result.startswith("orchestrating (")
        assert "Research report" in result

    def test_active_task_detection(self, svc):
        dashboard, project_svc, db = svc

        # Seed a being
        db.execute_commit(
            """INSERT INTO mc_beings (id,name,status,created_at,updated_at)
               VALUES (?,?,?,?,?)""",
            ("forge", "SAI Forge", "online", "2024-01-01", "2024-01-01"),
        )

        # Create a task assigned to forge
        task = dashboard.create_task(
            project_svc, title="Active task", status="in_progress",
            assignees=["forge"],
        )

        active = dashboard._get_being_active_task("forge")
        assert active is not None
        assert active["title"] == "Active task"

    def test_no_active_task(self, svc):
        dashboard, _, _ = svc
        active = dashboard._get_being_active_task("nonexistent-being")
        assert active is None
