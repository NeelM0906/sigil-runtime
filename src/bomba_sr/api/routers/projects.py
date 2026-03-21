"""Projects catalog router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/projects", tags=["projects"])


@router.get("/")
def list_projects(
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    projects = dashboard_svc.list_projects_catalog()
    return {"projects": projects}
