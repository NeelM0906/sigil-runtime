"""Skills router — catalog, install, list, executions."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bomba_sr.api.deps import get_bridge, get_current_user

router = APIRouter(prefix="/api/mc/skills", tags=["skills"])


# ── Request models ───────────────────────────────────────────────────

class InstallRequest(BaseModel):
    source: str
    skill_id: str
    reason: Optional[str] = None


# ── Catalog (non-parameterized paths first) ──────────────────────────

@router.get("/catalog/search")
def search_catalog(
    q: str = Query(""),
    source: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    catalog = bridge.list_skill_catalog(
        tenant_id=auth["tenant_id"],
        source=source,
    )
    query = q.strip().lower()
    if query:
        catalog = [
            s for s in catalog
            if query in s.get("name", "").lower() or query in s.get("description", "").lower()
        ]
    return {"results": catalog[:20], "count": len(catalog)}


@router.get("/catalog")
def list_catalog(
    source: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    catalog = bridge.list_skill_catalog(
        tenant_id=auth["tenant_id"],
        source=source,
        limit=limit,
    )
    return {"skills": catalog, "count": len(catalog)}


# ── Install ──────────────────────────────────────────────────────────

@router.get("/install")
def list_install_requests(
    status: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    requests = bridge.list_skill_install_requests(
        tenant_id=auth["tenant_id"],
        status=status,
    )
    return {"requests": requests}


@router.post("/install")
def create_install_request(
    body: InstallRequest,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    result = bridge.create_skill_install_request(
        tenant_id=auth["tenant_id"],
        user_id=auth["user_id"],
        source=body.source,
        skill_id=body.skill_id,
    )
    return {"request": result}


@router.post("/install/{request_id}/apply")
def apply_install(
    request_id: str,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    result = bridge.execute_skill_install(
        tenant_id=auth["tenant_id"],
        request_id=request_id,
    )
    return {"result": result}


# ── Executions ───────────────────────────────────────────────────────

@router.get("/executions")
def list_executions(
    limit: int = Query(100, ge=1, le=500),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    executions = bridge.list_skill_executions(
        tenant_id=auth["tenant_id"],
        limit=limit,
    )
    return {"executions": executions}


# ── Telemetry ────────────────────────────────────────────────────────

@router.get("/telemetry")
def list_telemetry(
    limit: int = Query(100, ge=1, le=500),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    telemetry = bridge.list_skill_telemetry(
        tenant_id=auth["tenant_id"],
        limit=limit,
    )
    return {"telemetry": telemetry}


# ── List / Detail ────────────────────────────────────────────────────

@router.get("")
def list_skills(
    status: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    skills = bridge.list_skills(
        tenant_id=auth["tenant_id"],
        status=status,
    )
    return {"skills": skills}


@router.get("/{skill_id}")
def get_skill(
    skill_id: str,
    auth: dict = Depends(get_current_user),
    bridge=Depends(get_bridge),
):
    try:
        runtime = bridge._tenant_runtime(auth["tenant_id"])
        record = runtime.skills_registry.get_skill(auth["tenant_id"], skill_id)
        return {
            "skill": {
                "skill_id": record.skill_id,
                "version": record.version,
                "name": record.name,
                "description": record.description,
                "status": record.status,
                "source": record.source,
                "source_path": record.source_path,
                "manifest": record.manifest,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        }
    except Exception:
        raise HTTPException(404, f"Skill not found: {skill_id}")
