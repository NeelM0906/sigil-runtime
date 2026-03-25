from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bomba_sr.skills.ecosystem import SkillEcosystemService
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _slugify_skill_id(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower()).strip("-")
    return value or "new-skill"


def _render_skill_md(
    *,
    name: str,
    description: str,
    body: str,
    user_invocable: bool,
    disable_model_invocation: bool,
    risk_level: str,
) -> str:
    safe_body = body.strip() or "Provide instructions for this skill."
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"user-invocable: {'true' if user_invocable else 'false'}",
        f"disable-model-invocation: {'true' if disable_model_invocation else 'false'}",
        f"risk-level: {risk_level}",
        "---",
        safe_body,
        "",
    ]
    return "\n".join(lines)


def builtin_skill_tools(
    loader: SkillLoader,
    registry: SkillRegistry,
    skills_ecosystem: SkillEcosystemService | None = None,
) -> list[ToolDefinition]:
    parser = SkillMdParser()

    def skill_create(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        raw_name = str(arguments.get("name") or arguments.get("skill_id") or "").strip()
        if not raw_name:
            raise ValueError("name is required")
        skill_id = _slugify_skill_id(str(arguments.get("skill_id") or raw_name))
        description = str(arguments.get("description") or "").strip()
        if not description:
            raise ValueError("description is required")
        body = str(arguments.get("body") or "").strip()
        overwrite = bool(arguments.get("overwrite", False))
        user_invocable = bool(arguments.get("user_invocable", True))
        disable_model_invocation = bool(arguments.get("disable_model_invocation", False))
        risk_level = str(arguments.get("risk_level") or "low").strip().lower()
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = "low"

        skill_dir = context.guard_path(Path("skills") / skill_id)
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists() and not overwrite:
            raise ValueError(f"skill already exists: {skill_id}. Pass overwrite=true to replace.")

        md = _render_skill_md(
            name=skill_id,
            description=description,
            body=body,
            user_invocable=user_invocable,
            disable_model_invocation=disable_model_invocation,
            risk_level=risk_level,
        )
        skill_file.write_text(md, encoding="utf-8")

        descriptor = parser.parse_file(skill_file, include_body=False)
        registry.register_from_descriptor(
            tenant_id=context.tenant_id,
            descriptor=descriptor,
            status=("active" if descriptor.default_enabled else "validated"),
        )
        loader.scan()
        if context.loop_state_ref is not None:
            context.loop_state_ref.tool_schemas_dirty = True
        return {
            "created": True,
            "skill_id": skill_id,
            "path": str(skill_file),
            "description": description,
            "user_invocable": user_invocable,
            "disable_model_invocation": disable_model_invocation,
        }

    def skill_update(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        skill_id = _slugify_skill_id(str(arguments.get("skill_id") or arguments.get("name") or "").strip())
        if not skill_id:
            raise ValueError("skill_id is required")
        skill_file = context.guard_path(Path("skills") / skill_id / "SKILL.md")
        if not skill_file.exists():
            raise ValueError(f"skill not found: {skill_id}")

        descriptor = parser.parse_file(skill_file, include_body=True)
        description = str(arguments.get("description") or descriptor.description).strip()
        body = str(arguments.get("body") or descriptor.body_text).strip()
        user_invocable = bool(arguments.get("user_invocable", descriptor.user_invocable))
        disable_model_invocation = bool(
            arguments.get("disable_model_invocation", descriptor.disable_model_invocation)
        )
        risk_level = str(arguments.get("risk_level") or descriptor.risk_level).strip().lower()
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = descriptor.risk_level

        md = _render_skill_md(
            name=skill_id,
            description=description,
            body=body,
            user_invocable=user_invocable,
            disable_model_invocation=disable_model_invocation,
            risk_level=risk_level,
        )
        skill_file.write_text(md, encoding="utf-8")

        updated = parser.parse_file(skill_file, include_body=False)
        registry.register_from_descriptor(
            tenant_id=context.tenant_id,
            descriptor=updated,
            status="active",
        )
        loader.scan()
        if context.loop_state_ref is not None:
            context.loop_state_ref.tool_schemas_dirty = True
        return {
            "updated": True,
            "skill_id": skill_id,
            "path": str(skill_file),
            "description": description,
        }

    def skill_list(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        status_filter = str(arguments.get("status") or "").strip() or None
        if status_filter == "all":
            status_filter = None
        skills = registry.list_skills(context.tenant_id, status=status_filter)
        return {
            "skills": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "version": s.version,
                    "status": s.status,
                    "source": s.source,
                }
                for s in skills
            ],
            "count": len(skills),
        }

    tools: list[ToolDefinition] = [
        ToolDefinition(
            name="skill_list",
            description="List all installed skills for this tenant. Optionally filter by status (active, draft, validated, or all).",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "draft", "validated", "all"]},
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=skill_list,
        ),
        ToolDefinition(
            name="skill_create",
            description="Create a SKILL.md skill in workspace/skills and register it for the tenant.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "skill_id": {"type": "string"},
                    "description": {"type": "string"},
                    "body": {"type": "string"},
                    "user_invocable": {"type": "boolean"},
                    "disable_model_invocation": {"type": "boolean"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "overwrite": {"type": "boolean"},
                },
                "required": ["name", "description"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=skill_create,
        ),
        ToolDefinition(
            name="skill_update",
            description="Update an existing workspace skill SKILL.md and re-register it.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "body": {"type": "string"},
                    "user_invocable": {"type": "boolean"},
                    "disable_model_invocation": {"type": "boolean"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                },
                "required": ["skill_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=skill_update,
        ),
    ]

    return tools
