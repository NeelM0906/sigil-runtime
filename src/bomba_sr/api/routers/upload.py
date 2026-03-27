"""File upload router — extract text, store in memory, return to frontend."""
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

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".txt", ".md", ".csv", ".tsv",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".php", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".sql", ".json", ".xml", ".yaml", ".yml",
    ".sh", ".bash", ".css", ".scss",
}
MAX_SIZE = 50 * 1024 * 1024


@router.post("")
def upload_file(
    file: UploadFile = File(...),
    being_id: str = Form("recovery"),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    from bomba_sr.ingestion.ingest import ingest_to_memory, ingest_to_pinecone_background
    from bomba_sr.ingestion.parser import extract_text
    from bomba_sr.memory.hybrid import HybridMemoryStore
    from bomba_sr.runtime.tenancy import TenantRegistry
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.tools.builtin_pinecone import _load_tenant_pinecone_map

    # Read file (sync — FastAPI runs def endpoints in threadpool)
    contents = file.file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 50MB)")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Save to temp file for extraction
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Extract text (fast — no ML models)
        extracted = extract_text(tmp_path)
        text = extracted.get("text", "")
        can_native = extracted.get("can_send_native", False)

        # Only reject if text extraction failed AND format can't be sent natively to LLM
        if not can_native and (not text or text.startswith("[Could not extract") or text.startswith("[Binary file")):
            raise HTTPException(
                422,
                f"Could not extract text from {file.filename}. "
                f"Format: {extracted.get('format', 'unknown')}. "
                f"Detail: {text}",
            )

        # Native-capable files with no extracted text (scanned PDFs, images)
        if not text and can_native:
            text = f"[Native document: {file.filename} — content readable by LLM via direct file access]"
            extracted["text"] = text
            extracted["_is_native_placeholder"] = True

        # Get tenant's memory store
        runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
        registry = TenantRegistry(runtime_home)
        being = dashboard_svc.get_being(being_id) or {}
        tenant_id = being.get("tenant_id") or auth["tenant_id"]
        context = registry.ensure_tenant(tenant_id)
        db = RuntimeDB(context.db_path)
        memory_store = HybridMemoryStore(db=db, memory_root=context.memory_root)

        # Store in local memory
        result = ingest_to_memory(
            extracted=extracted,
            tenant_id=tenant_id,
            user_id=auth["user_id"],
            being_id=being_id,
            filename=file.filename or "unknown",
            memory_store=memory_store,
            consolidator=memory_store.consolidator,
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

        if extracted.get("_is_native_placeholder"):
            result["text_extracted"] = False
            result["note"] = "Scanned/image PDF — no text extracted. File saved for manual processing."

        # Background: embed into Pinecone (skip native placeholders)
        pc_map = _load_tenant_pinecone_map()
        pc_cfg = pc_map.get(auth["tenant_id"], {})
        if pc_cfg.get("index") and pc_cfg.get("namespace") and extracted.get("text") and not extracted.get("_is_native_placeholder"):
            ingest_to_pinecone_background(
                text=extracted["text"],
                doc_id=result["doc_id"],
                tenant_id=tenant_id,
                being_id=being_id,
                filename=file.filename or "unknown",
                index=pc_cfg["index"],
                namespace=pc_cfg["namespace"],
            )
            result["pinecone"] = "embedding in background"

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


@router.post("/batch")
def upload_files_batch(
    files: list[UploadFile] = File(...),
    being_id: str = Form("recovery"),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    """Upload multiple files in one request (max 10)."""
    from bomba_sr.ingestion.ingest import ingest_to_memory, ingest_to_pinecone_background
    from bomba_sr.ingestion.parser import extract_text
    from bomba_sr.memory.hybrid import HybridMemoryStore
    from bomba_sr.runtime.tenancy import TenantRegistry
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.tools.builtin_pinecone import _load_tenant_pinecone_map

    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per upload")

    runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
    registry = TenantRegistry(runtime_home)
    being = dashboard_svc.get_being(being_id) or {}
    tenant_id = being.get("tenant_id") or auth["tenant_id"]
    context = registry.ensure_tenant(tenant_id)
    db = RuntimeDB(context.db_path)
    memory_store = HybridMemoryStore(db=db, memory_root=context.memory_root)
    pc_map = _load_tenant_pinecone_map()
    pc_cfg = pc_map.get(auth["tenant_id"], {})
    being_ws = dashboard_svc._resolve_workspace_path(being.get("workspace"))

    results = []
    errors = []

    for file in files:
        contents = file.file.read()
        if len(contents) > MAX_SIZE:
            errors.append({"filename": file.filename, "error": "File too large (max 50MB)"})
            continue
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append({"filename": file.filename, "error": f"Unsupported type: {ext}"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            extracted = extract_text(tmp_path)
            text = extracted.get("text", "")
            can_native = extracted.get("can_send_native", False)
            if not can_native and (not text or text.startswith("[Could not extract") or text.startswith("[Binary file")):
                errors.append({"filename": file.filename, "error": f"Extraction failed: {text[:200]}"})
                continue
            if not text and can_native:
                text = f"[Native document: {file.filename}]"
                extracted["text"] = text
                extracted["_is_native_placeholder"] = True

            result = ingest_to_memory(
                extracted=extracted,
                tenant_id=tenant_id,
                user_id=auth["user_id"],
                being_id=being_id,
                filename=file.filename or "unknown",
                memory_store=memory_store,
                consolidator=memory_store.consolidator,
            )
            if being_ws:
                uploads_dir = being_ws / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                base_name = file.filename or f"upload-{result['doc_id']}{ext}"
                dest = uploads_dir / base_name
                # Avoid overwriting files with the same name
                if dest.exists():
                    stem = Path(base_name).stem
                    suffix = Path(base_name).suffix
                    dest = uploads_dir / f"{stem}-{result['doc_id'][:8]}{suffix}"
                shutil.copy2(tmp_path, str(dest))
                result["saved_to"] = str(dest)

            if extracted.get("_is_native_placeholder"):
                result["text_extracted"] = False
                result["note"] = "Scanned/image PDF — no text extracted. File saved for manual processing."

            if pc_cfg.get("index") and pc_cfg.get("namespace") and text and not extracted.get("_is_native_placeholder"):
                ingest_to_pinecone_background(
                    text=text, doc_id=result["doc_id"],
                    tenant_id=tenant_id, being_id=being_id,
                    filename=file.filename or "unknown",
                    index=pc_cfg["index"], namespace=pc_cfg["namespace"],
                )
            results.append(result)
        except Exception as exc:
            errors.append({"filename": file.filename, "error": str(exc)})
        finally:
            os.unlink(tmp_path)

    db.close()
    return {"results": results, "errors": errors, "total": len(files), "succeeded": len(results)}
