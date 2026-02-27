from __future__ import annotations

from typing import Any, Callable

from bomba_sr.tools.base import ToolContext, ToolDefinition


AddScheduleFn = Callable[[str, str, str, str, str | None, bool], dict[str, Any]]
ListSchedulesFn = Callable[[str, str, str | None, bool], list[dict[str, Any]]]
RemoveScheduleFn = Callable[[str, str, str, str | None], dict[str, Any]]
SetScheduleEnabledFn = Callable[[str, str, str, bool, str | None], dict[str, Any]]


def builtin_scheduler_tools(
    add_schedule: AddScheduleFn,
    list_schedules: ListSchedulesFn,
    remove_schedule: RemoveScheduleFn,
    set_schedule_enabled: SetScheduleEnabledFn,
) -> list[ToolDefinition]:
    def _schedule_task(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        expression = str(arguments.get("cron_expression") or "").strip()
        goal = str(arguments.get("task_goal") or "").strip()
        enabled = bool(arguments.get("enabled", True))
        created = add_schedule(
            context.tenant_id,
            context.user_id,
            expression,
            goal,
            str(context.workspace_root),
            enabled,
        )
        return {"created": created}

    def _list_schedules(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        include_disabled = bool(arguments.get("include_disabled", True))
        rows = list_schedules(
            context.tenant_id,
            context.user_id,
            str(context.workspace_root),
            include_disabled,
        )
        return {"schedules": rows}

    def _remove_schedule(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        task_id = str(arguments.get("task_id") or "").strip()
        if not task_id:
            raise ValueError("task_id is required")
        return remove_schedule(context.tenant_id, context.user_id, task_id, str(context.workspace_root))

    def _set_schedule_enabled(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        task_id = str(arguments.get("task_id") or "").strip()
        if not task_id:
            raise ValueError("task_id is required")
        enabled = bool(arguments.get("enabled", True))
        return set_schedule_enabled(
            context.tenant_id,
            context.user_id,
            task_id,
            enabled,
            str(context.workspace_root),
        )

    return [
        ToolDefinition(
            name="schedule_task",
            description="Schedule a recurring proactive task using a cron expression.",
            parameters={
                "type": "object",
                "properties": {
                    "cron_expression": {"type": "string"},
                    "task_goal": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["cron_expression", "task_goal"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_schedule_task,
        ),
        ToolDefinition(
            name="list_schedules",
            description="List existing recurring scheduled tasks.",
            parameters={
                "type": "object",
                "properties": {
                    "include_disabled": {"type": "boolean"},
                },
                "required": [],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_schedules,
        ),
        ToolDefinition(
            name="remove_schedule",
            description="Remove a recurring scheduled task by id.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_remove_schedule,
        ),
        ToolDefinition(
            name="set_schedule_enabled",
            description="Enable or disable a recurring scheduled task by id.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["task_id", "enabled"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_set_schedule_enabled,
        ),
    ]
