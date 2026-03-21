"""SSE events router."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/events", tags=["events"])


def _auth_from_token_query(request: Request, token: Optional[str] = Query(None)) -> dict:
    """SSE auth: try Bearer header first, fall back to ?token= query param.

    EventSource API cannot send custom headers, so the frontend appends
    the token as a query parameter.
    """
    # Try normal header auth first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        tok = auth_header[7:]
    elif token:
        tok = token
    else:
        raise HTTPException(401, "Unauthorized")

    svc = request.app.state.dashboard_svc
    if not svc:
        raise HTTPException(503, "Dashboard service not initialized")
    row = svc.db.execute(
        "SELECT s.user_id, s.expires_at, u.tenant_id, u.role "
        "FROM mc_sessions_auth s "
        "JOIN mc_users u ON u.id = s.user_id "
        "WHERE s.token = ?",
        (tok,),
    ).fetchone()
    if not row:
        raise HTTPException(401, "Unauthorized")
    expires = row["expires_at"]
    if expires and expires < datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, "Token expired")
    return {"user_id": row["user_id"], "tenant_id": row["tenant_id"], "role": row["role"]}


@router.get("")
def event_stream(
    auth: dict = Depends(_auth_from_token_query),
    dashboard_svc=Depends(get_dashboard_svc),
):
    client_id = dashboard_svc.subscribe_sse(tenant_id=auth["tenant_id"])

    def generate():
        try:
            while True:
                evt = dashboard_svc.poll_sse(client_id, timeout=20.0)
                if evt is None:
                    yield ": keepalive\n\n"
                    continue
                line = json.dumps(evt["data"], default=str)
                yield f"event: {evt['event']}\ndata: {line}\n\n"
        except (GeneratorExit, BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            dashboard_svc.unsubscribe_sse(client_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
