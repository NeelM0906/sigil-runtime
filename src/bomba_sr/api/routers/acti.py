"""ACT-I architecture router — read-only data endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from bomba_sr.api.deps import get_current_user

router = APIRouter(prefix="/api/mc/acti", tags=["acti"])


@router.get("/architecture")
def get_architecture(auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import get_full_architecture
    return get_full_architecture()


@router.get("/beings")
def list_acti_beings(auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import load_beings
    return {"beings": load_beings()}


@router.get("/beings/{being_id}")
def get_acti_being(being_id: str, auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import load_beings
    beings = load_beings()
    match = next((b for b in beings if b["id"] == being_id), None)
    if not match:
        raise HTTPException(404, "ACT-I being not found")
    return {"being": match}


@router.get("/clusters")
def list_clusters(
    family: Optional[str] = Query(None),
    being: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
):
    from bomba_sr.acti.loader import load_clusters
    clusters = load_clusters()
    if family:
        clusters = [c for c in clusters if c["family"] == family]
    if being:
        clusters = [c for c in clusters if c["being"] == being]
    return {"clusters": clusters}


@router.get("/skill-families")
def list_skill_families(auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import load_skill_families
    return {"skill_families": load_skill_families()}


@router.get("/levers")
def list_levers(auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import LEVERS, load_lever_matrix
    return {"levers": LEVERS, "matrix": load_lever_matrix()}


@router.get("/sisters/{sister_id}")
def get_sister_profile(sister_id: str, auth: dict = Depends(get_current_user)):
    from bomba_sr.acti.loader import get_sister_profile
    profile = get_sister_profile(sister_id)
    if not profile["beings"]:
        raise HTTPException(404, "No ACT-I beings mapped to this sister")
    return {"sister_id": sister_id, "profile": profile}
