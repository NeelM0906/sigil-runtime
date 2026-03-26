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


def builtin_deliverable_tools() -> list[ToolDefinition]:
    return [
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
