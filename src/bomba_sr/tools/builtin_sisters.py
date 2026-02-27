from __future__ import annotations

from typing import Any, Callable

from bomba_sr.tools.base import ToolContext, ToolDefinition


def _list_factory(list_sisters: Callable[[], list[dict[str, Any]]]):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = arguments
        _ = context
        return {"sisters": list_sisters()}

    return run


def _spawn_factory(spawn_sister: Callable[[str], dict[str, Any]]):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        sister_id = str(arguments.get("sister_id") or "").strip()
        if not sister_id:
            raise ValueError("sister_id is required")
        return spawn_sister(sister_id)

    return run


def _stop_factory(stop_sister: Callable[[str], dict[str, Any]]):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        sister_id = str(arguments.get("sister_id") or "").strip()
        if not sister_id:
            raise ValueError("sister_id is required")
        return stop_sister(sister_id)

    return run


def _status_factory(sister_status: Callable[[str], dict[str, Any]]):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        sister_id = str(arguments.get("sister_id") or "").strip()
        if not sister_id:
            raise ValueError("sister_id is required")
        return sister_status(sister_id)

    return run


def _message_factory(message_sister: Callable[[str, str], dict[str, Any]]):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        sister_id = str(arguments.get("sister_id") or "").strip()
        message = str(arguments.get("message") or "").strip()
        if not sister_id:
            raise ValueError("sister_id is required")
        if not message:
            raise ValueError("message is required")
        return message_sister(sister_id, message)

    return run


def builtin_sister_tools(
    *,
    list_sisters: Callable[[], list[dict[str, Any]]],
    spawn_sister: Callable[[str], dict[str, Any]],
    stop_sister: Callable[[str], dict[str, Any]],
    sister_status: Callable[[str], dict[str, Any]],
    message_sister: Callable[[str, str], dict[str, Any]],
) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="sisters_list",
            description="List configured sisters and their current status.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            risk_level="low",
            action_type="read",
            execute=_list_factory(list_sisters),
        ),
        ToolDefinition(
            name="sisters_spawn",
            description="Start a configured sister background sub-agent.",
            parameters={
                "type": "object",
                "properties": {"sister_id": {"type": "string"}},
                "required": ["sister_id"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_spawn_factory(spawn_sister),
        ),
        ToolDefinition(
            name="sisters_stop",
            description="Stop a running sister background sub-agent.",
            parameters={
                "type": "object",
                "properties": {"sister_id": {"type": "string"}},
                "required": ["sister_id"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_stop_factory(stop_sister),
        ),
        ToolDefinition(
            name="sisters_status",
            description="Get detailed status for a sister.",
            parameters={
                "type": "object",
                "properties": {"sister_id": {"type": "string"}},
                "required": ["sister_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_status_factory(sister_status),
        ),
        ToolDefinition(
            name="sisters_message",
            description="Send a message to a sister workspace and return her response.",
            parameters={
                "type": "object",
                "properties": {
                    "sister_id": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["sister_id", "message"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=_message_factory(message_sister),
        ),
    ]
