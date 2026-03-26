"""Being tool for explicitly registering deliverables/outputs."""
from __future__ import annotations

import mimetypes
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


def _register_deliverable(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Register a file as a user-facing deliverable/output."""
    file_path = str(arguments.get("file_path") or "").strip()
    title = str(arguments.get("title") or "").strip()
    description = str(arguments.get("description") or "").strip()

    if not file_path:
        raise ValueError("file_path is required")

    resolved = context.guard_path(file_path)
    if not resolved.exists():
        raise ValueError(f"File not found: {file_path}")

    filename = resolved.name
    file_size = resolved.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(resolved))

    return {
        "registered": True,
        "file_path": str(resolved),
        "filename": filename,
        "title": title or filename,
        "description": description,
        "mime_type": mime_type or "application/octet-stream",
        "file_size": file_size,
        "_is_deliverable": True,
    }


def _list_deliverables(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """List existing deliverables/outputs from previous tasks."""
    import os
    from bomba_sr.storage.factory import create_shared_db

    search = str(arguments.get("search") or "").strip().lower()
    limit = int(arguments.get("limit") or 20)

    db = create_shared_db()
    try:
        if search:
            rows = db.execute(
                "SELECT id, filename, file_type, file_path, url, task_id, session_id, created_at "
                "FROM mc_deliverables WHERE LOWER(filename) LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{search}%", limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, filename, file_type, file_path, url, task_id, session_id, created_at "
                "FROM mc_deliverables ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        items = []
        for r in rows:
            d = dict(r)
            fpath = d.get("file_path", "")
            exists = os.path.isfile(fpath) if fpath else False
            items.append({
                "id": d["id"],
                "filename": d["filename"],
                "file_type": d["file_type"],
                "file_path": fpath,
                "url": d.get("url", ""),
                "exists_on_disk": exists,
                "created_at": d.get("created_at", ""),
            })
        return {"deliverables": items, "count": len(items)}
    finally:
        db.close()


def builtin_deliverable_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="list_deliverables",
            description=(
                "Search and list existing deliverables/outputs from previous tasks. "
                "Use when a user asks 'where are my files?', 'can I get the MP4s?', "
                "'show me what was generated'. Returns file paths and download URLs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Optional search term to filter by filename (e.g., 'mp4', 'video', 'lance')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20)",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_deliverables,
        ),
        ToolDefinition(
            name="create_deliverable",
            description=(
                "Register a file as a user-facing output/deliverable. Use this "
                "AFTER creating a file (via exec, write, or any other method) that "
                "the user should be able to see, download, or interact with. "
                "Examples: a generated video, a report PDF, an analysis spreadsheet, "
                "a chart image, a processed document. "
                "Do NOT use for internal workspace files (KNOWLEDGE.md, SKILL.md, etc). "
                "Only register files that ARE the work product the user asked for."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to register as output. Can be absolute or relative to workspace.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable title for the output (e.g., 'Sunrise Mountain Video', 'Q3 Revenue Analysis')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this output contains.",
                    },
                },
                "required": ["file_path", "title"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_register_deliverable,
        ),
    ]
