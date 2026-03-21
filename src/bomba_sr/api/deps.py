"""FastAPI dependencies — auth, service accessors."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer()


def get_dashboard_svc(request: Request):
    svc = request.app.state.dashboard_svc
    if svc is None:
        raise HTTPException(status_code=503, detail="dashboard service not initialized")
    return svc


def get_project_svc(request: Request):
    svc = request.app.state.project_svc
    if svc is None:
        raise HTTPException(status_code=503, detail="project service not initialized")
    return svc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    dashboard_svc=Depends(get_dashboard_svc),
) -> dict:
    """Validate Bearer token and return {user_id, tenant_id, role}.

    Raises HTTPException(401) on invalid/expired token.
    """
    token = credentials.credentials
    row = dashboard_svc.db.execute(
        "SELECT s.user_id, s.expires_at, u.tenant_id, u.role "
        "FROM mc_sessions_auth s "
        "JOIN mc_users u ON u.id = s.user_id "
        "WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if row["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=401, detail="Token expired")
    return {"user_id": row["user_id"], "tenant_id": row["tenant_id"], "role": row["role"]}
