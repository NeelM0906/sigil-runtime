"""Workspace file manager — browse, upload, preview, delete files in being workspaces."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mc/workspace", tags=["workspace"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".txt", ".md", ".csv", ".tsv",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".php", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".sql", ".json", ".xml", ".yaml", ".yml",
    ".sh", ".bash", ".css", ".scss",
}
MAX_SIZE = 50 * 1024 * 1024

EXT_CATEGORIES = {
    ".pdf": "document", ".docx": "document", ".pptx": "document",
    ".xlsx": "spreadsheet", ".xls": "spreadsheet", ".csv": "spreadsheet", ".tsv": "spreadsheet",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".webp": "image",
    ".html": "code", ".txt": "text", ".md": "text",
    ".php": "code", ".py": "code", ".js": "code", ".jsx": "code",
    ".ts": "code", ".tsx": "code", ".sql": "code", ".json": "data",
    ".xml": "data", ".yaml": "data", ".yml": "data",
    ".sh": "code", ".bash": "code", ".css": "code", ".scss": "code",
}


def _get_workspace_uploads(dashboard_svc, being_id: str) -> Path | None:
    being = dashboard_svc.get_being(being_id) or {}
    ws = dashboard_svc._resolve_workspace_path(being.get("workspace"))
    if not ws:
        return None
    uploads = ws / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    return uploads


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.get("/files")
def list_workspace_files(
    being_id: str = Query("recovery"),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    """List all files in a being's workspace uploads directory."""
    uploads = _get_workspace_uploads(dashboard_svc, being_id)
    if not uploads or not uploads.exists():
        return {"files": [], "being_id": being_id}

    files = []
    for f in sorted(uploads.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file():
            stat = f.stat()
            ext = f.suffix.lower()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "modified": stat.st_mtime,
                "extension": ext,
                "category": EXT_CATEGORIES.get(ext, "other"),
            })
    return {"files": files, "being_id": being_id, "total": len(files)}


@router.delete("/files")
def delete_workspace_file(
    being_id: str = Query(...),
    filename: str = Query(...),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    """Delete a file from a being's workspace uploads directory."""
    uploads = _get_workspace_uploads(dashboard_svc, being_id)
    if not uploads:
        raise HTTPException(404, "Workspace not found")

    target = uploads / filename
    # Prevent path traversal
    if ".." in filename or not target.resolve().is_relative_to(uploads.resolve()):
        raise HTTPException(400, "Invalid filename")
    if not target.exists():
        raise HTTPException(404, f"File not found: {filename}")

    target.unlink()
    log.info("workspace file deleted: %s/%s by user %s", being_id, filename, auth["user_id"])
    return {"deleted": filename, "being_id": being_id}


@router.get("/files/preview")
def preview_workspace_file(
    being_id: str = Query(...),
    filename: str = Query(...),
    max_chars: int = Query(8000),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    """Preview text content of a workspace file."""
    uploads = _get_workspace_uploads(dashboard_svc, being_id)
    if not uploads:
        raise HTTPException(404, "Workspace not found")

    target = uploads / filename
    if ".." in filename or not target.resolve().is_relative_to(uploads.resolve()):
        raise HTTPException(400, "Invalid filename")
    if not target.exists():
        raise HTTPException(404, f"File not found: {filename}")

    ext = target.suffix.lower()
    category = EXT_CATEGORIES.get(ext, "other")

    # Images — no text preview
    if category == "image":
        return {
            "filename": filename,
            "category": category,
            "preview": None,
            "message": "Image files cannot be previewed as text.",
        }

    # Try extraction for documents
    if ext in {".pdf", ".docx", ".pptx", ".xlsx", ".xls"}:
        try:
            from bomba_sr.ingestion.parser import extract_text
            extracted = extract_text(str(target))
            text = extracted.get("text", "")
            if not text:
                return {"filename": filename, "category": category, "preview": None,
                        "message": "Could not extract text from this file."}
            truncated = len(text) > max_chars
            return {"filename": filename, "category": category,
                    "preview": text[:max_chars], "truncated": truncated,
                    "total_chars": len(text)}
        except Exception as exc:
            return {"filename": filename, "category": category, "preview": None,
                    "message": f"Extraction error: {exc}"}

    # Text/code files — read directly
    try:
        text = target.read_text(errors="replace")
        truncated = len(text) > max_chars
        return {"filename": filename, "category": category,
                "preview": text[:max_chars], "truncated": truncated,
                "total_chars": len(text)}
    except Exception as exc:
        return {"filename": filename, "category": category, "preview": None,
                "message": f"Read error: {exc}"}


@router.post("/upload")
def upload_to_workspace(
    files: list[UploadFile] = File(...),
    being_id: str = Form("recovery"),
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    """Upload files directly to a being's workspace and optionally index them."""
    from bomba_sr.ingestion.ingest import ingest_to_memory, ingest_to_pinecone_background
    from bomba_sr.ingestion.parser import extract_text
    from bomba_sr.memory.hybrid import HybridMemoryStore
    from bomba_sr.runtime.tenancy import TenantRegistry
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.tools.builtin_pinecone import _load_tenant_pinecone_map

    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per upload")

    uploads = _get_workspace_uploads(dashboard_svc, being_id)
    if not uploads:
        raise HTTPException(404, "Workspace not found for this being")

    # Set up memory + pinecone for indexing
    runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
    registry = TenantRegistry(runtime_home)
    being = dashboard_svc.get_being(being_id) or {}
    tenant_id = being.get("tenant_id") or auth["tenant_id"]
    context = registry.ensure_tenant(tenant_id)
    db = RuntimeDB(context.db_path)
    memory_store = HybridMemoryStore(db=db, memory_root=context.memory_root)
    pc_map = _load_tenant_pinecone_map()
    pc_cfg = pc_map.get(tenant_id, {})

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

        # Save to workspace
        dest = uploads / (file.filename or f"upload{ext}")
        if dest.exists():
            stem = Path(file.filename).stem
            import uuid
            dest = uploads / f"{stem}-{uuid.uuid4().hex[:8]}{ext}"
        dest.write_bytes(contents)

        result = {
            "filename": dest.name,
            "size": len(contents),
            "size_display": _format_size(len(contents)),
            "extension": ext,
            "category": EXT_CATEGORIES.get(ext, "other"),
            "saved_to": str(dest),
            "indexed": False,
        }

        # Try to extract text and index for memory/pinecone
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            extracted = extract_text(tmp_path)
            text = extracted.get("text", "")
            if text and not text.startswith("[Could not extract") and not text.startswith("[Binary file"):
                mem_result = ingest_to_memory(
                    extracted=extracted,
                    tenant_id=tenant_id,
                    user_id=auth["user_id"],
                    being_id=being_id,
                    filename=dest.name,
                    memory_store=memory_store,
                    consolidator=memory_store.consolidator,
                )
                result["indexed"] = True
                result["chunks"] = mem_result.get("chunks", 0)
                result["doc_id"] = mem_result.get("doc_id")

                if pc_cfg.get("index") and pc_cfg.get("namespace"):
                    ingest_to_pinecone_background(
                        text=text, doc_id=mem_result["doc_id"],
                        tenant_id=tenant_id, being_id=being_id,
                        filename=dest.name,
                        index=pc_cfg["index"], namespace=pc_cfg["namespace"],
                    )
                    result["pinecone"] = "embedding in background"
        except Exception as exc:
            log.warning("indexing failed for %s: %s", dest.name, exc)
        finally:
            os.unlink(tmp_path)

        results.append(result)

    db.close()
    log.info("workspace upload: %d files to %s by %s", len(results), being_id, auth["user_id"])
    return {"results": results, "errors": errors, "total": len(files), "succeeded": len(results)}
