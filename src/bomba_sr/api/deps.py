"""FastAPI dependencies — auth, service accessors."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request


def get_dashboard_svc(request: Request):
    svc = request.app.state.dashboard_svc
    if not svc:
        raise HTTPException(503, "Dashboard service not initialized")
    return svc


def get_project_svc(request: Request):
    svc = request.app.state.project_svc
    if not svc:
        raise HTTPException(503, "Project service not initialized")
    return svc


def get_bridge(request: Request):
    return request.app.state.bridge


def get_current_user(request: Request) -> dict[str, Any]:
    """Extract Bearer token, validate, return {user_id, tenant_id, role}.

    Raises HTTPException(401) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")
    token = auth_header[7:]
    svc = request.app.state.dashboard_svc
    if not svc:
        raise HTTPException(503, "Dashboard service not initialized")
    row = svc.db.execute(
        "SELECT s.user_id, s.expires_at, u.tenant_id, u.role "
        "FROM mc_sessions_auth s "
        "JOIN mc_users u ON u.id = s.user_id "
        "WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(401, "Unauthorized")
    expires = row["expires_at"]
    if expires and expires < datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, "Token expired")
    return {"user_id": row["user_id"], "tenant_id": row["tenant_id"], "role": row["role"]}


def require_admin(auth: dict = Depends(get_current_user)) -> dict:
    if auth.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return auth
