"""Deliverables router."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/deliverables", tags=["deliverables"])


@router.get("/")
def list_deliverables(
    task_id: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    if task_id:
        deliverables = dashboard_svc.list_deliverables(task_id, tenant_id=auth["tenant_id"])
    else:
        deliverables = dashboard_svc.list_all_deliverables(tenant_id=auth["tenant_id"])
    return {"deliverables": deliverables}
