"""File upload router — parse, ingest, and index documents."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mc/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg"}
MAX_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    being_id: str = Form("recovery"),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    from bomba_sr.ingestion.ingest import ingest_document
    from bomba_sr.ingestion.parser import parse_document
    from bomba_sr.memory.hybrid import HybridMemoryStore
    from bomba_sr.runtime.tenancy import TenantRegistry
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.tools.builtin_pinecone import _load_tenant_pinecone_map

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 50MB)")

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Parse
        parsed = parse_document(tmp_path)

        # Get tenant's memory store
        runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
        registry = TenantRegistry(runtime_home)
        being = dashboard_svc.get_being(being_id) or {}
        tenant_id = being.get("tenant_id") or auth["tenant_id"]
        context = registry.ensure_tenant(tenant_id)
        db = RuntimeDB(context.db_path)
        memory_store = HybridMemoryStore(db=db, memory_root=context.memory_root)
        consolidator = memory_store.consolidator

        # Check Pinecone config for this tenant
        pc_map = _load_tenant_pinecone_map()
        pc_cfg = pc_map.get(auth["tenant_id"], {})

        # Ingest
        result = ingest_document(
            parsed=parsed,
            tenant_id=tenant_id,
            user_id=auth["user_id"],
            being_id=being_id,
            filename=file.filename or "unknown",
            memory_store=memory_store,
            consolidator=consolidator,
            pinecone_index=pc_cfg.get("index"),
            pinecone_namespace=pc_cfg.get("namespace"),
        )

        db.close()

        # Save original file to being's workspace
        being_ws = dashboard_svc._resolve_workspace_path(being.get("workspace"))
        if being_ws:
            uploads_dir = being_ws / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            dest = uploads_dir / (file.filename or f"upload-{result['doc_id']}{ext}")
            shutil.copy2(tmp_path, str(dest))
            result["saved_to"] = str(dest)

        # Inject context into the being's memory so it knows the document was uploaded
        summary_lines = parsed["markdown"][:500].replace("\n", " ").strip()
        context_note = (
            f"[DOCUMENT UPLOADED] {file.filename or 'unknown'} — "
            f"{result['chunks']} chunks indexed into your semantic memory, "
            f"{result['tables']} tables extracted. "
            f"Content preview: {summary_lines[:200]}..."
        )
        try:
            memory_store.append_working_note(
                user_id=auth["user_id"],
                session_id=f"upload-context-{result['doc_id']}",
                title=f"Upload context: {file.filename}",
                content=context_note,
                tags=["upload", "context", file.filename or "unknown"],
                confidence=1.0,
                being_id=being_id,
            )
        except Exception:
            pass  # Non-critical

        return result
    finally:
        os.unlink(tmp_path)


@router.get("/files")
def list_uploaded_files(
    being_id: str = "recovery",
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    being = dashboard_svc.get_being(being_id) or {}
    ws = dashboard_svc._resolve_workspace_path(being.get("workspace"))
    if not ws:
        return {"files": []}
    uploads_dir = ws / "uploads"
    if not uploads_dir.exists():
        return {"files": []}
    files = []
    for f in sorted(uploads_dir.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return {"files": files}
