"""WebSocket endpoint for real-time bidirectional communication."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with tenant scoping."""

    def __init__(self):
        self._connections: dict[str, dict] = {}
        # client_id -> {"ws": WebSocket, "tenant_id": str, "user_id": str, "queue": asyncio.Queue}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str, websocket: WebSocket, tenant_id: str, user_id: str):
        await websocket.accept()
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._connections[client_id] = {
                "ws": websocket,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "queue": q,
            }
        log.info("[WS] Client connected: %s (tenant=%s, user=%s)", client_id, tenant_id, user_id)

    async def disconnect(self, client_id: str):
        async with self._lock:
            self._connections.pop(client_id, None)
        log.info("[WS] Client disconnected: %s", client_id)

    def emit_event_sync(self, event_type: str, payload: dict, tenant_id: str | None = None):
        """Called from synchronous code (dashboard service, orchestration engine).
        Thread-safe: asyncio.Queue.put_nowait is safe from any thread."""
        evt = {"event": event_type, "data": payload, "ts": datetime.now(timezone.utc).isoformat()}
        dead = []
        for cid, entry in list(self._connections.items()):
            if tenant_id is not None and entry.get("tenant_id") and entry["tenant_id"] != tenant_id:
                continue
            try:
                entry["queue"].put_nowait(evt)
            except asyncio.QueueFull:
                dead.append(cid)
        for cid in dead:
            self._connections.pop(cid, None)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# Singleton
manager = ConnectionManager()


def _authenticate_ws(token: str, dashboard_svc) -> dict | None:
    """Validate a WebSocket auth token. Returns user dict or None."""
    if not token:
        return None
    row = dashboard_svc.db.execute(
        "SELECT s.user_id, s.expires_at, u.tenant_id, u.role, u.name "
        "FROM mc_sessions_auth s "
        "JOIN mc_users u ON u.id = s.user_id "
        "WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not row:
        return None
    expires = row["expires_at"]
    if expires and expires < datetime.now(timezone.utc).isoformat():
        return None
    return {
        "user_id": row["user_id"],
        "tenant_id": row["tenant_id"],
        "role": row["role"],
        "name": row["name"],
    }


async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """Main WebSocket handler. Auth via ?token= query param."""
    dashboard_svc = websocket.app.state.dashboard_svc
    if not dashboard_svc:
        await websocket.close(code=1011, reason="Service unavailable")
        return

    auth = _authenticate_ws(token, dashboard_svc)
    if not auth:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    client_id = str(uuid.uuid4())
    await manager.connect(client_id, websocket, auth["tenant_id"], auth["user_id"])

    async def send_loop():
        entry = manager._connections.get(client_id)
        if not entry:
            return
        ws = entry["ws"]
        q = entry["queue"]
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=25.0)
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json(evt)
                except asyncio.TimeoutError:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json({"event": "keepalive", "ts": datetime.now(timezone.utc).isoformat()})
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass

    async def recv_loop():
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                if msg_type == "ping":
                    await websocket.send_json({"event": "pong", "ts": datetime.now(timezone.utc).isoformat()})
        except (WebSocketDisconnect, RuntimeError, OSError, json.JSONDecodeError):
            pass

    try:
        done, pending = await asyncio.wait(
            [asyncio.create_task(send_loop()), asyncio.create_task(recv_loop())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await manager.disconnect(client_id)
