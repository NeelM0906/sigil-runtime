"""Deliverables and artifacts router."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc", tags=["deliverables"])


def _auth_header_or_query(request: Request, token: Optional[str] = Query(None)) -> dict:
    """Auth via Bearer header or ?token= query param (for browser downloads)."""
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


@router.get("/deliverables")
def list_deliverables(
    task_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    if task_id:
        deliverables = dashboard_svc.list_deliverables(task_id, tenant_id=auth["tenant_id"])
    elif session_id:
        deliverables = dashboard_svc.list_session_deliverables(session_id, tenant_id=auth["tenant_id"])
    else:
        deliverables = dashboard_svc.list_all_deliverables(tenant_id=auth["tenant_id"])
    return {"deliverables": deliverables}


def _find_artifact(artifact_id: str, dashboard_svc, tenant_id: str | None = None):
    """Find artifact in shared DB first, then fall back to per-tenant SQLite DBs."""
    rec = dashboard_svc.get_artifact(artifact_id)
    if rec:
        return rec
    # Fall back: search per-tenant DBs
    import os
    from bomba_sr.storage.db import RuntimeDB
    tenants_dir = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime")) / "tenants"
    if not tenants_dir.is_dir():
        return None
    # If we know the tenant, check that one first
    dirs = []
    if tenant_id:
        t = tenants_dir / tenant_id / "runtime" / "runtime.db"
        if t.is_file():
            dirs.append(t)
    # Then check all tenants
    for td in tenants_dir.iterdir():
        db_path = td / "runtime" / "runtime.db"
        if db_path.is_file() and db_path not in dirs:
            dirs.append(db_path)
    for db_path in dirs:
        try:
            db = RuntimeDB(db_path)
            row = db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
            if row:
                return dict(row)
        except Exception:
            pass
    return None


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    auth: dict = Depends(_auth_header_or_query),
    dashboard_svc=Depends(get_dashboard_svc),
):
    rec = _find_artifact(artifact_id, dashboard_svc, auth.get("tenant_id"))
    if not rec:
        raise HTTPException(404, "Artifact not found")
    fpath = Path(rec["path"])
    if not fpath.is_file():
        raise HTTPException(404, "Artifact file missing")
    return FileResponse(
        path=str(fpath),
        filename=rec.get("filename") or fpath.name,
        media_type=rec.get("mime_type") or "application/octet-stream",
    )


@router.get("/artifacts/{artifact_id}/preview")
def preview_artifact(
    artifact_id: str,
    auth: dict = Depends(_auth_header_or_query),
    dashboard_svc=Depends(get_dashboard_svc),
):
    rec = _find_artifact(artifact_id, dashboard_svc, auth.get("tenant_id"))
    if not rec:
        raise HTTPException(404, "Artifact not found")
    fpath = Path(rec["path"])
    if not fpath.is_file():
        raise HTTPException(404, "Artifact file missing")
    from bomba_sr.artifacts.store import get_artifact_type_info
    _, _, is_binary = get_artifact_type_info(rec.get("artifact_type", ""))
    if is_binary:
        return {
            "type": "binary",
            "download_url": f"/api/mc/artifacts/{artifact_id}/download",
            "mime_type": rec.get("mime_type", "application/octet-stream"),
            "artifact": rec,
        }
    content = fpath.read_text(encoding="utf-8", errors="replace")[:50000]
    return {
        "type": "text",
        "content": content,
        "mime_type": rec.get("mime_type", "text/plain"),
        "artifact": rec,
    }
