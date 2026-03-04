"""Tool for beings to update their own KNOWLEDGE.md file.

This is a self-editable knowledge block (inspired by Letta's memory blocks).
Unlike SOUL.md and IDENTITY.md which are read-only identity, KNOWLEDGE.md
is the being's evolving knowledge base — updated as the being learns.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

KNOWLEDGE_MAX_CHARS = 4000

_KNOWLEDGE_TEMPLATE = """\
# Knowledge Base
*Self-maintained. Updated as I learn.*

## Key Facts

## Domain Expertise

## Learned Patterns
"""


def _update_knowledge_factory():
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        section = str(arguments.get("section") or "").strip()
        content = str(arguments.get("content") or "").strip()
        if not section or not content:
            raise ValueError("section and content are required")

        kb_path = Path(context.workspace_root) / "KNOWLEDGE.md"

        # Read or create
        if kb_path.exists():
            text = kb_path.read_text(encoding="utf-8")
        else:
            text = _KNOWLEDGE_TEMPLATE

        # Find the section heading and replace its content
        # Sections are delimited by ## headings
        pattern = re.compile(
            rf"(^## {re.escape(section)}\s*\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            new_text = pattern.sub(rf"\g<1>{content}\n\n", text, count=1)
        else:
            # Append as a new section
            new_text = text.rstrip() + f"\n\n## {section}\n{content}\n"

        # Enforce size cap
        if len(new_text) > KNOWLEDGE_MAX_CHARS:
            new_text = new_text[:KNOWLEDGE_MAX_CHARS]

        kb_path.write_text(new_text, encoding="utf-8")

        return {
            "status": "updated",
            "section": section,
            "file": str(kb_path),
            "total_chars": len(new_text),
            "cap": KNOWLEDGE_MAX_CHARS,
        }

    return run


def builtin_knowledge_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="update_knowledge",
            description=(
                "Update a section of your KNOWLEDGE.md file — your persistent, self-editable "
                "knowledge base. Use this to record key facts, domain expertise, and learned "
                "patterns that should persist across sessions. Sections: 'Key Facts', "
                "'Domain Expertise', 'Learned Patterns', or any custom section name."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "The section heading to update (e.g., 'Key Facts', 'Domain Expertise').",
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
            execute=_update_knowledge_factory(),
        ),
    ]
