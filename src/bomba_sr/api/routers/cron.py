"""Cron scheduler router — manage scheduled tasks via REST API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bomba_sr.api.deps import get_bridge, get_current_user

router = APIRouter(prefix="/api/mc/cron", tags=["cron"])


class CreateCronTaskRequest(BaseModel):
    task_goal: str
    cron_expression: Optional[str] = None
    schedule_type: str = "cron"
    run_at: Optional[str] = None
    interval_seconds: Optional[int] = None
    delete_after_run: bool = False
    enabled: bool = True


class UpdateCronTaskRequest(BaseModel):
    enabled: Optional[bool] = None


def _get_scheduler(auth, bridge):
    scheduler = bridge._ensure_cron_scheduler(
        tenant_id=auth["tenant_id"], user_id=auth["user_id"],
    )
    return scheduler


@router.get("/status")
def cron_status(auth: dict = Depends(get_current_user), bridge=Depends(get_bridge)):
    scheduler = _get_scheduler(auth, bridge)
    return scheduler.status()


@router.get("/tasks")
def list_cron_tasks(auth: dict = Depends(get_current_user), bridge=Depends(get_bridge)):
    scheduler = _get_scheduler(auth, bridge)
    return {"tasks": scheduler.list_tasks(include_disabled=True)}


@router.post("/tasks", status_code=201)
def create_cron_task(
    body: CreateCronTaskRequest,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    scheduler = _get_scheduler(auth, bridge)
    scheduler.start()
    task = scheduler.add_task(
        cron_expression=body.cron_expression or "",
        task_goal=body.task_goal,
        enabled=body.enabled,
        schedule_type=body.schedule_type,
        run_at=body.run_at,
        interval_seconds=body.interval_seconds,
        delete_after_run=body.delete_after_run,
    )
    return {"task": task}


@router.get("/tasks/{task_id}/runs")
def get_cron_runs(
    task_id: str,
    limit: int = Query(20, ge=1, le=100),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    scheduler = _get_scheduler(auth, bridge)
    return {"runs": scheduler.get_runs(task_id, limit=limit)}


@router.post("/tasks/{task_id}/run")
def force_run_task(
    task_id: str,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    scheduler = _get_scheduler(auth, bridge)
    tasks = scheduler.list_tasks()
    target = next((t for t in tasks if t["id"] == task_id), None)
    if not target:
        raise HTTPException(404, "Task not found")
    try:
        result = scheduler.runner(target["task_goal"], task_id)
        return {"result": result or {}}
    except Exception as exc:
        raise HTTPException(500, f"Run failed: {exc}")


@router.patch("/tasks/{task_id}")
def update_cron_task(
    task_id: str,
    body: UpdateCronTaskRequest,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    scheduler = _get_scheduler(auth, bridge)
    if body.enabled is not None:
        scheduler.set_enabled(task_id, body.enabled)
    return {"updated": True, "task_id": task_id}


@router.delete("/tasks/{task_id}")
def delete_cron_task(
    task_id: str,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    scheduler = _get_scheduler(auth, bridge)
    return scheduler.remove_task(task_id)
