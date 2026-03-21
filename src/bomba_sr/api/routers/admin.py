"""Admin router — dream cycle, audit log."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from bomba_sr.api.deps import get_bridge, get_dashboard_svc, require_admin

router = APIRouter(prefix="/api/mc", tags=["admin"])


class DreamCycleRequest(BaseModel):
    being_id: Optional[str] = None


@router.post("/dream-cycle")
def trigger_dream_cycle(
    body: DreamCycleRequest,
    auth: dict = Depends(require_admin),
    bridge=Depends(get_bridge),
    dashboard_svc=Depends(get_dashboard_svc),
):
    result = bridge.dream_cycle_run_once(
        being_id=body.being_id,
        dashboard_svc=dashboard_svc,
    )
    return {"dream_cycle": result}


@router.get("/dream-cycle/logs")
def list_dream_logs(
    limit: int = Query(20),
    auth: dict = Depends(require_admin),
):
    from bomba_sr.memory.dreaming import DreamCycle
    logs = DreamCycle.list_dream_logs(limit=limit)
    return {"logs": logs}


@router.get("/dream-cycle/status")
def dream_cycle_status(
    auth: dict = Depends(require_admin),
    bridge=Depends(get_bridge),
):
    return {"dream_cycle": bridge.dream_cycle_status()}


@router.get("/audit")
def query_audit_log(
    tenant_id: Optional[str] = Query(None),
    being_id: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    limit: int = Query(100),
    auth: dict = Depends(require_admin),
    dashboard_svc=Depends(get_dashboard_svc),
):
    sql = "SELECT * FROM tool_audit_log WHERE 1=1"
    params: list = []
    if tenant_id:
        sql += " AND tenant_id = ?"
        params.append(tenant_id)
    if being_id:
        sql += " AND being_id = ?"
        params.append(being_id)
    if tool_name:
        sql += " AND tool_name = ?"
        params.append(tool_name)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    try:
        rows = dashboard_svc.db.execute(sql, params).fetchall()
        return {"entries": [dict(r) for r in rows]}
    except Exception:
        return {"entries": []}
