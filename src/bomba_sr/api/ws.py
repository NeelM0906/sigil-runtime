"""WebSocket endpoint for real-time bidirectional communication."""
from __future__ import annotations

import asyncio
import json
import logging
import queue as thread_queue
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with tenant + session scoping."""

    def __init__(self):
        self._connections: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str, websocket: WebSocket, tenant_id: str, user_id: str):
        q = thread_queue.Queue(maxsize=500)
        notify = asyncio.Event()
        loop = asyncio.get_event_loop()
        async with self._lock:
            self._connections[client_id] = {
                "ws": websocket,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "queue": q,
                "notify": notify,
                "loop": loop,
                "session_ids": set(),
            }
        log.info("[WS] Client connected: %s (tenant=%s, user=%s)", client_id, tenant_id, user_id)

    async def disconnect(self, client_id: str):
        async with self._lock:
            self._connections.pop(client_id, None)
        log.info("[WS] Client disconnected: %s", client_id)

    def subscribe_session(self, client_id: str, session_id: str):
        entry = self._connections.get(client_id)
        if entry:
            entry["session_ids"].add(session_id)

    def unsubscribe_session(self, client_id: str, session_id: str):
        entry = self._connections.get(client_id)
        if entry:
            entry["session_ids"].discard(session_id)

    def emit_event_sync(
        self, event_type: str, payload: dict,
        tenant_id: str | None = None, session_id: str | None = None,
    ):
        """Called from ANY thread. Thread-safe via stdlib Queue + call_soon_threadsafe."""
        # Roundtrip through JSON to ensure no datetime objects survive to send_json
        try:
            safe_payload = json.loads(json.dumps(payload, default=str))
        except (TypeError, ValueError):
            safe_payload = payload
        evt = {"event": event_type, "data": safe_payload, "ts": datetime.now(timezone.utc).isoformat()}
        dead = []
        delivered: set[str] = set()
        for cid, entry in list(self._connections.items()):
            should_deliver = False
            # Tenant match (existing)
            if tenant_id is None:
                should_deliver = True
            elif not entry.get("tenant_id") or entry["tenant_id"] == tenant_id:
                should_deliver = True
            # Session match (shared sessions)
            if session_id and session_id in entry.get("session_ids", set()):
                should_deliver = True
            if should_deliver and cid not in delivered:
                try:
                    entry["queue"].put_nowait(evt)
                    entry["loop"].call_soon_threadsafe(entry["notify"].set)
                    delivered.add(cid)
                except thread_queue.Full:
                    dead.append(cid)
                except RuntimeError:
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
    await websocket.accept()

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
        notify = entry["notify"]
        try:
            while True:
                try:
                    await asyncio.wait_for(notify.wait(), timeout=25.0)
                    notify.clear()
                except asyncio.TimeoutError:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json({"event": "keepalive", "ts": datetime.now(timezone.utc).isoformat()})
                    continue
                # Drain all queued events
                while True:
                    try:
                        evt = q.get_nowait()
                        if ws.client_state == WebSocketState.CONNECTED:
                            await ws.send_json(evt)
                    except thread_queue.Empty:
                        break
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass

    async def recv_loop():
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                if msg_type == "ping":
                    await websocket.send_json({"event": "pong", "ts": datetime.now(timezone.utc).isoformat()})
                elif msg_type == "subscribe_session":
                    sid = data.get("session_id")
                    if sid:
                        manager.subscribe_session(client_id, sid)
                        await websocket.send_json({"event": "subscribed", "session_id": sid})
                elif msg_type == "unsubscribe_session":
                    sid = data.get("session_id")
                    if sid:
                        manager.unsubscribe_session(client_id, sid)
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
