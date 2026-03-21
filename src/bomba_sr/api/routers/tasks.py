"""Tasks router — CRUD, children, steps, artifacts, history, cleanup."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bomba_sr.api.deps import get_current_user, get_dashboard_svc, get_project_svc

router = APIRouter(prefix="/api/mc/tasks", tags=["tasks"])


# ── Request models ───────────────────────────────────────────────────

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "backlog"
    priority: str = "medium"
    assignees: Optional[list[str]] = None
    owner_agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignees: Optional[list[str]] = None
    owner_agent_id: Optional[str] = None


# ── List / History / Cleanup (non-parameterized paths first) ─────────

@router.get("/history")
def task_history(
    taskId: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    history = dashboard_svc.task_history(task_id=taskId)
    return {"history": history}


@router.post("/cleanup")
def cleanup_tasks(
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    deleted = dashboard_svc.clean_casual_tasks(project_svc, tenant_id=auth["tenant_id"])
    return {"deleted": deleted}


@router.get("/")
def list_tasks(
    assignee: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    top_level_only: bool = Query(True),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
    # "from" and "to" are Python keywords — use alias
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    tasks = dashboard_svc.list_tasks(
        project_svc,
        tenant_id=auth["tenant_id"],
        assignee=assignee,
        priority=priority,
        status=status,
        from_date=from_date,
        to_date=to_date,
        top_level_only=top_level_only,
    )
    return {"tasks": tasks}


# ── Create ───────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_task(
    body: CreateTaskRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    task = dashboard_svc.create_task(
        project_svc,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        assignees=body.assignees,
        owner_agent_id=body.owner_agent_id,
        parent_task_id=body.parent_task_id,
        tenant_id=auth["tenant_id"],
    )
    return {"task": task}


# ── Single task + sub-resources ──────────────────────────────────────

@router.get("/{task_id}/steps")
def get_task_steps(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    steps = dashboard_svc.get_task_steps(task_id)
    return {"steps": steps}


@router.get("/{task_id}/artifacts")
def get_task_artifacts(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    artifacts = dashboard_svc.list_task_artifacts(task_id, tenant_id=auth["tenant_id"])
    return {"artifacts": artifacts}


@router.get("/{task_id}/children")
def get_task_children(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    child_ids = dashboard_svc.get_task_children(task_id, tenant_id=auth["tenant_id"])
    children = []
    for cid in child_ids:
        try:
            children.append(dashboard_svc.get_task(project_svc, cid, tenant_id=auth["tenant_id"]))
        except Exception:
            children.append({"id": cid, "status": "unknown"})
    return {"children": children, "parent_task_id": task_id}


@router.get("/{task_id}/orchestration")
def get_task_orchestration(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    task = dashboard_svc.get_task_with_orchestration(
        project_svc, task_id, tenant_id=auth["tenant_id"],
    )
    return {"task": task}


@router.get("/{task_id}")
def get_task(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    task = dashboard_svc.get_task(project_svc, task_id, tenant_id=auth["tenant_id"])
    return {"task": task}


# ── Update ───────────────────────────────────────────────────────────

@router.patch("/{task_id}")
def update_task(
    task_id: str,
    body: UpdateTaskRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    task = dashboard_svc.update_task(
        project_svc,
        task_id,
        status=body.status,
        priority=body.priority,
        owner_agent_id=body.owner_agent_id,
        assignees=body.assignees,
        title=body.title,
        description=body.description,
        tenant_id=auth["tenant_id"],
    )
    return {"task": task}


# ── Delete ───────────────────────────────────────────────────────────

@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
    project_svc=Depends(get_project_svc),
):
    ok = dashboard_svc.delete_task(project_svc, task_id, tenant_id=auth["tenant_id"])
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"ok": True}
