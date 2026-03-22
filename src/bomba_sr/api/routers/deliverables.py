"""Deliverables and artifacts router."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc", tags=["deliverables"])


@router.get("/deliverables")
def list_deliverables(
    task_id: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    if task_id:
        deliverables = dashboard_svc.list_deliverables(task_id, tenant_id=auth["tenant_id"])
    else:
        deliverables = dashboard_svc.list_all_deliverables(tenant_id=auth["tenant_id"])
    return {"deliverables": deliverables}


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    rec = dashboard_svc.get_artifact(artifact_id)
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
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    rec = dashboard_svc.get_artifact(artifact_id)
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
