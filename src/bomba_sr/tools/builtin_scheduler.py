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
        schedule_type = str(arguments.get("schedule_type") or "cron").strip().lower()
        run_at = arguments.get("run_at")
        interval_seconds = arguments.get("interval_seconds")
        delete_after_run = bool(arguments.get("delete_after_run", False))
        try:
            created = add_schedule(
                context.tenant_id,
                context.user_id,
                expression,
                goal,
                str(context.workspace_root),
                enabled,
                schedule_type=schedule_type,
                run_at=run_at,
                interval_seconds=interval_seconds,
                delete_after_run=delete_after_run,
            )
        except TypeError:
            # Fallback for bridge versions that don't yet accept the new kwargs
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
            description=(
                "Schedule a task to run automatically. Supports three schedule types:\n"
                "  - cron: recurring via cron expression (e.g. '*/30 * * * *' = every 30min, "
                "'0 9 * * *' = daily at 9am, '@hourly', '@daily')\n"
                "  - at: one-shot at a specific ISO datetime (e.g. '2026-03-26T14:00:00Z'), "
                "auto-deleted after execution\n"
                "  - every: recurring at a fixed interval in seconds (e.g. 3600 = every hour)\n"
                "Examples:\n"
                "  {schedule_type: 'cron', cron_expression: '0 */6 * * *', task_goal: 'Check pipeline status'}\n"
                "  {schedule_type: 'at', run_at: '2026-03-26T09:00:00Z', task_goal: 'Send morning report'}\n"
                "  {schedule_type: 'every', interval_seconds: 1800, task_goal: 'Poll inbox'}"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "schedule_type": {
                        "type": "string",
                        "enum": ["cron", "at", "every"],
                        "description": "Type of schedule: 'cron' (recurring cron), 'at' (one-shot datetime), 'every' (fixed interval).",
                    },
                    "cron_expression": {
                        "type": "string",
                        "description": "Cron expression (required for schedule_type='cron'). E.g. '*/30 * * * *', '@hourly', '@daily'.",
                    },
                    "task_goal": {
                        "type": "string",
                        "description": "Natural-language description of what the task should do when it fires.",
                    },
                    "run_at": {
                        "type": "string",
                        "description": "ISO-8601 datetime for one-shot execution (required for schedule_type='at'). E.g. '2026-03-26T14:00:00Z'.",
                    },
                    "interval_seconds": {
                        "type": "integer",
                        "description": "Interval in seconds between runs (required for schedule_type='every'). Minimum 1.",
                    },
                    "delete_after_run": {
                        "type": "boolean",
                        "description": "If true, delete the task after it runs once. Defaults to true for 'at' type, false otherwise.",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether the schedule starts enabled. Defaults to true.",
                    },
                },
                "required": ["task_goal"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_schedule_task,
        ),
        ToolDefinition(
            name="list_schedules",
            description="List existing scheduled tasks with their next run times, types, and status.",
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
            description="Remove a scheduled task by id.",
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
            description="Enable or disable a scheduled task by id.",
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
