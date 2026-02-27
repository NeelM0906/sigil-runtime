from __future__ import annotations

from typing import Any

from bomba_sr.governance.tool_profiles import TOOL_GROUPS, resolve_alias
from bomba_sr.tools.base import ToolContext, ToolDefinition


def builtin_discovery_tools() -> list[ToolDefinition]:
    def enable_tools(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        state = context.loop_state_ref
        if state is None:
            raise ValueError("loop_state_unavailable")

        raw_groups = arguments.get("groups")
        if not isinstance(raw_groups, list) or not raw_groups:
            raise ValueError("groups must be a non-empty list")

        enabled: list[str] = []
        denied: list[str] = []
        already_active: list[str] = []
        overrides = getattr(state, "active_tool_overrides", set())
        denied_tools = getattr(state, "denied_tools", set())

        for group in raw_groups:
            group_name = str(group).strip()
            if not group_name:
                continue
            tools = TOOL_GROUPS.get(group_name)
            if tools is None:
                denied.append(group_name)
                continue
            for tool_name in sorted(tools):
                canonical = resolve_alias(tool_name)
                if canonical in denied_tools:
                    denied.append(canonical)
                    continue
                if canonical in overrides:
                    already_active.append(canonical)
                    continue
                overrides.add(canonical)
                enabled.append(canonical)

        setattr(state, "active_tool_overrides", overrides)
        return {
            "enabled": enabled,
            "denied": denied,
            "already_active": already_active,
            "reason": str(arguments.get("reason") or ""),
        }

    return [
        ToolDefinition(
            name="enable_tools",
            description="Enable additional tool groups for later loop iterations.",
            parameters={
                "type": "object",
                "properties": {
                    "groups": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
                "required": ["groups"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=enable_tools,
        )
    ]
