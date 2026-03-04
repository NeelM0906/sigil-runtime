"""Tool for Prime to update the shared TEAM_CONTEXT.md file.

TEAM_CONTEXT.md lives at the workspaces root (not per-being) and is
read by all sisters but writable only by Prime.  This provides passive
cross-being awareness without explicit broadcast.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

TEAM_CONTEXT_MAX_CHARS = 3000

_TEAM_CONTEXT_TEMPLATE = """\
# Team Context
*Maintained by SAI Prime. Read by all sisters.*

## Active Priorities

## Recent Task Outcomes

## Cross-Being Notes
"""


def _resolve_team_context_path(workspace_root: Path) -> Path:
    """Return the TEAM_CONTEXT.md path at the workspaces root.

    From any being's workspace (e.g. workspaces/forge), walk up to find
    the shared workspaces/ directory.
    """
    root = Path(workspace_root).resolve()
    # If we're already AT the workspaces dir (has TEAM_CONTEXT.md)
    candidate = root / "TEAM_CONTEXT.md"
    if candidate.exists():
        return candidate
    # Walk up: being workspace is workspaces/<name>, so parent is workspaces/
    parent = root.parent
    candidate = parent / "TEAM_CONTEXT.md"
    if candidate.exists():
        return candidate
    # Fallback: create at parent (workspaces/) level
    return parent / "TEAM_CONTEXT.md"


def _update_team_context_factory():
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        section = str(arguments.get("section") or "").strip()
        content = str(arguments.get("content") or "").strip()
        if not section or not content:
            raise ValueError("section and content are required")

        # Prime-only gate: only tenant-prime / tenant-local can write
        tid = (context.tenant_id or "").lower()
        if "prime" not in tid and tid != "tenant-local":
            raise PermissionError(
                "Only Prime can update TEAM_CONTEXT.md. "
                f"Your tenant ({context.tenant_id}) does not have write access."
            )

        tc_path = _resolve_team_context_path(context.workspace_root)

        # Read or create
        if tc_path.exists():
            text = tc_path.read_text(encoding="utf-8")
        else:
            text = _TEAM_CONTEXT_TEMPLATE

        # Find the section heading and replace its content
        pattern = re.compile(
            rf"(^## {re.escape(section)}\s*\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            new_text = pattern.sub(rf"\g<1>{content}\n\n", text, count=1)
        else:
            new_text = text.rstrip() + f"\n\n## {section}\n{content}\n"

        # Enforce size cap
        if len(new_text) > TEAM_CONTEXT_MAX_CHARS:
            new_text = new_text[:TEAM_CONTEXT_MAX_CHARS]

        tc_path.write_text(new_text, encoding="utf-8")

        return {
            "status": "updated",
            "section": section,
            "file": str(tc_path),
            "total_chars": len(new_text),
            "cap": TEAM_CONTEXT_MAX_CHARS,
        }

    return run


def builtin_team_context_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="update_team_context",
            description=(
                "Update a section of the shared TEAM_CONTEXT.md file — the team-wide "
                "context block readable by all beings. Only Prime can write to this. "
                "Use to broadcast priorities, recent task outcomes, and cross-being notes. "
                "Sections: 'Active Priorities', 'Recent Task Outcomes', 'Cross-Being Notes', "
                "or any custom section."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "The section heading to update (e.g., 'Active Priorities').",
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content for this section. Replaces existing section content.",
                    },
                },
                "required": ["section", "content"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_update_team_context_factory(),
        ),
    ]
