"""Chat router — sessions, messages, system messages."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bomba_sr.api.deps import get_current_user, get_dashboard_svc, require_admin

router = APIRouter(prefix="/api/mc/chat", tags=["chat"])


# ── Request models ───────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    name: str = "New Chat"


class RenameSessionRequest(BaseModel):
    name: str


class SendMessageRequest(BaseModel):
    content: str = ""
    targets: list[str] = []
    mode: Optional[str] = "auto"
    taskRef: Optional[str] = None
    session_id: Optional[str] = None


class SystemMessageRequest(BaseModel):
    content: str = ""
    taskRef: Optional[str] = None


# ── Sessions ─────────────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    sessions = dashboard_svc.list_sessions(user_id=auth["user_id"])
    return {"sessions": sessions}


@router.post("/sessions", status_code=201)
def create_session(
    body: CreateSessionRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    session = dashboard_svc.create_session(
        body.name, user_id=auth["user_id"], tenant_id=auth["tenant_id"],
    )
    return {"session": session}


@router.patch("/sessions/{session_id}")
def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    existing = dashboard_svc.get_session(session_id)
    if not existing or existing.get("user_id") != auth["user_id"]:
        raise HTTPException(403, "Forbidden")
    session = dashboard_svc.rename_session(
        session_id, body.name, tenant_id=auth["tenant_id"],
    )
    return {"session": session}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    existing = dashboard_svc.get_session(session_id)
    if not existing or existing.get("user_id") != auth["user_id"]:
        raise HTTPException(403, "Forbidden")
    ok = dashboard_svc.delete_session(session_id, tenant_id=auth["tenant_id"])
    if not ok:
        raise HTTPException(404, "Session not found or is default")
    return {"ok": True}


# ── Messages ─────────────────────────────────────────────────────────

@router.get("/messages")
def list_messages(
    sender: Optional[str] = Query(None),
    target: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(500),
    offset: int = Query(0),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    msgs = dashboard_svc.list_messages(
        sender=sender,
        target=target,
        search=search,
        session_id=session_id,
        user_id=auth["user_id"],
        limit=limit,
        offset=offset,
    )
    return {"messages": msgs}


@router.post("/messages", status_code=201)
def send_message(
    body: SendMessageRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    sender = auth["user_id"]
    targets = body.targets
    session_id = body.session_id or f"sess-{uuid.uuid4().hex}"

    # Auto-route broadcast (no targets) to prime
    if not targets:
        targets = ["prime"]

    msg_type = "broadcast"
    if len(targets) == 1:
        msg_type = "direct"
    elif len(targets) > 1:
        msg_type = "group"

    msg = dashboard_svc.create_message(
        sender=sender,
        content=body.content,
        targets=targets,
        msg_type=msg_type,
        mode=body.mode or "auto",
        task_ref=body.taskRef,
        session_id=session_id,
        tenant_id=auth["tenant_id"],
    )

    # Route to each targeted being in background
    for tid in targets:
        dashboard_svc.route_to_being(tid, body.content, sender=sender, chat_session_id=session_id)

    return {"message": msg}


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    # Ownership check via session
    msg_row = dashboard_svc.db.execute(
        "SELECT m.session_id FROM mc_messages m "
        "JOIN mc_chat_sessions s ON s.id = m.session_id "
        "WHERE m.id = ? AND s.user_id = ?",
        (message_id, auth["user_id"]),
    ).fetchone()
    if not msg_row:
        raise HTTPException(403, "Forbidden")
    ok = dashboard_svc.delete_message(message_id)
    if not ok:
        raise HTTPException(404, "Message not found")
    return {"ok": True}


# ── System messages (admin only) ─────────────────────────────────────

@router.post("/system", status_code=201)
def system_message(
    body: SystemMessageRequest,
    auth: dict = Depends(require_admin),
    dashboard_svc=Depends(get_dashboard_svc),
):
    msg = dashboard_svc.create_system_message(
        content=body.content,
        task_ref=body.taskRef,
    )
    return {"message": msg}
