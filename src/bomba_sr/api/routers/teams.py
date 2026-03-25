"""Teams router — CRUD, members, sharing, channels."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


class ShareSessionRequest(BaseModel):
    session_id: str


class CreateChannelRequest(BaseModel):
    name: str


def _require_team_admin(team: dict, user_id: str) -> None:
    if not team:
        raise HTTPException(404, "Team not found")
    is_admin = any(
        m["user_id"] == user_id and m["role"] == "admin"
        for m in team.get("members", [])
    )
    if not is_admin:
        raise HTTPException(403, "Team admin required")


@router.get("")
def list_teams(
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    teams = dashboard_svc.list_user_teams(auth["user_id"])
    return {"teams": teams}


@router.post("", status_code=201)
def create_team(
    body: CreateTeamRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    team = dashboard_svc.create_team(
        name=body.name,
        admin_user_id=auth["user_id"],
        description=body.description or "",
    )
    return {"team": team}


@router.get("/{team_id}")
def get_team(
    team_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    team = dashboard_svc.get_team(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    return {"team": team}


@router.post("/{team_id}/members")
def add_member(
    team_id: str,
    body: AddMemberRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    team = dashboard_svc.get_team(team_id)
    _require_team_admin(team, auth["user_id"])
    result = dashboard_svc.add_team_member(team_id, body.user_id, body.role)
    return result


@router.delete("/{team_id}/members/{user_id}")
def remove_member(
    team_id: str,
    user_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    team = dashboard_svc.get_team(team_id)
    _require_team_admin(team, auth["user_id"])
    return dashboard_svc.remove_team_member(team_id, user_id)


@router.post("/{team_id}/share")
def share_session(
    team_id: str,
    body: ShareSessionRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    # Any team member can share
    team = dashboard_svc.get_team(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    is_member = any(m["user_id"] == auth["user_id"] for m in team.get("members", []))
    if not is_member:
        raise HTTPException(403, "Not a team member")
    return dashboard_svc.share_session_with_team(
        session_id=body.session_id,
        team_id=team_id,
        shared_by=auth["user_id"],
    )


@router.get("/{team_id}/channels")
def list_channels(
    team_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    return {"channels": dashboard_svc.list_team_channels(team_id)}


@router.post("/{team_id}/channels", status_code=201)
def create_channel(
    team_id: str,
    body: CreateChannelRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    team = dashboard_svc.get_team(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    is_member = any(m["user_id"] == auth["user_id"] for m in team.get("members", []))
    if not is_member:
        raise HTTPException(403, "Not a team member")
    return dashboard_svc.create_team_channel(team_id, body.name, auth["user_id"])
