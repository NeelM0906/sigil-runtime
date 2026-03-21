"""Subagents router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/subagents", tags=["subagents"])


@router.get("")
def list_subagent_runs(
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    runs = dashboard_svc.list_subagent_runs(tenant_id=auth["tenant_id"])
    return {"runs": runs}
