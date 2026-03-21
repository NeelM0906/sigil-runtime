"""Beings router — list, get, detail, file, skills, update."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/beings", tags=["beings"])


@router.get("/")
def list_beings(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    beings = dashboard_svc.list_beings(type_filter=type, status_filter=status)
    return {"beings": beings}


@router.get("/{being_id}/detail")
def get_being_detail(
    being_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    detail = dashboard_svc.get_being_detail(being_id)
    if not detail:
        raise HTTPException(404, "Being not found")
    return detail


@router.get("/{being_id}/file")
def get_being_file(
    being_id: str,
    path: str = Query(...),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    content = dashboard_svc.get_being_file(being_id, path)
    if content is None:
        raise HTTPException(404, "File not found")
    return {"content": content, "path": path}


@router.get("/{being_id}/skills")
def get_being_skills(
    being_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    skills = dashboard_svc.get_being_skill_list(being_id)
    return {"skills": skills}


@router.get("/{being_id}")
def get_being(
    being_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    being = dashboard_svc.get_being(being_id)
    if not being:
        raise HTTPException(404, "Being not found")
    return {"being": being}


@router.patch("/{being_id}")
def update_being(
    being_id: str,
    body: dict[str, Any],
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    being = dashboard_svc.update_being(being_id, body)
    if not being:
        raise HTTPException(404, "Being not found")
    return {"being": being}
