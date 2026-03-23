"""Orchestration router — start, status, log."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from bomba_sr.api.deps import get_current_user, get_dashboard_svc, get_project_svc

router = APIRouter(prefix="/api/mc/orchestration", tags=["orchestration"])


class StartOrchestrationRequest(BaseModel):
    goal: str
    session_id: str = "mc-chat-prime"
    strategy: Optional[str] = None
    beings: Optional[list[str]] = None


@router.post("", status_code=201)
def start_orchestration(
    body: StartOrchestrationRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    if not dashboard_svc.orchestration_engine:
        raise HTTPException(503, "Orchestration engine not initialized")
    result = dashboard_svc.orchestration_engine.start(
        goal=body.goal,
        requester_session_id=body.session_id,
        sender=auth["user_id"],
        tenant_id=auth["tenant_id"],
    )
    return {"orchestration": result}


@router.get("/{task_id}/status")
def get_orchestration_status(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    # Verify orchestration task belongs to this tenant
    row = dashboard_svc.db.execute(
        "SELECT 1 FROM project_tasks WHERE task_id = ? AND tenant_id = ?",
        (task_id, auth["tenant_id"]),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Orchestration not found")
    status = dashboard_svc.get_orchestration_status(task_id)
    if status is None:
        raise HTTPException(404, "Orchestration not found")
    return {"orchestration": status}


@router.get("/{task_id}/log")
def get_orchestration_log(
    task_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    row = dashboard_svc.db.execute(
        "SELECT 1 FROM project_tasks WHERE task_id = ? AND tenant_id = ?",
        (task_id, auth["tenant_id"]),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Orchestration not found")
    log_entries = dashboard_svc.get_orchestration_log(task_id)
    return {"log": log_entries}
