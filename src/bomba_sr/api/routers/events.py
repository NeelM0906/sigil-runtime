"""SSE events router."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/events", tags=["events"])


@router.get("/")
def event_stream(
    auth: dict = Depends(get_current_user),
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
