"""Skills router — list, detail, executions, telemetry."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from bomba_sr.api.deps import get_bridge, get_current_user

router = APIRouter(prefix="/api/mc/skills", tags=["skills"])


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
