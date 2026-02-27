from __future__ import annotations

from typing import Any

from bomba_sr.projects.service import ProjectService
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _project_create_factory(projects: ProjectService):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        name = str(arguments.get("name") or "").strip()
        workspace_root = str(arguments.get("workspace_root") or context.workspace_root)
        if not name:
            raise ValueError("name is required")
        return projects.create_project(
            tenant_id=context.tenant_id,
            name=name,
            workspace_root=workspace_root,
            description=(str(arguments["description"]) if arguments.get("description") else None),
            project_id=(str(arguments["project_id"]) if arguments.get("project_id") else None),
            status=str(arguments.get("status") or "active"),
        )

    return run


def _project_list_factory(projects: ProjectService):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        return {"projects": projects.list_projects(context.tenant_id)}

    return run


def _task_create_factory(projects: ProjectService):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        project_id = str(arguments.get("project_id") or "").strip()
        title = str(arguments.get("title") or "").strip()
        if not project_id or not title:
            raise ValueError("project_id and title are required")
        return projects.create_task(
            tenant_id=context.tenant_id,
            project_id=project_id,
            title=title,
            description=(str(arguments["description"]) if arguments.get("description") else None),
            task_id=(str(arguments["task_id"]) if arguments.get("task_id") else None),
            status=str(arguments.get("status") or "todo"),
            priority=str(arguments.get("priority") or "normal"),
            owner_agent_id=(str(arguments["owner_agent_id"]) if arguments.get("owner_agent_id") else None),
        )

    return run


def _task_list_factory(projects: ProjectService):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        return {
            "tasks": projects.list_tasks(
                tenant_id=context.tenant_id,
                project_id=(str(arguments["project_id"]) if arguments.get("project_id") else None),
                status=(str(arguments["status"]) if arguments.get("status") else None),
            )
        }

    return run


def _task_update_factory(projects: ProjectService):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        task_id = str(arguments.get("task_id") or "").strip()
        if not task_id:
            raise ValueError("task_id is required")
        return projects.update_task(
            tenant_id=context.tenant_id,
            task_id=task_id,
            status=(str(arguments["status"]) if arguments.get("status") else None),
            priority=(str(arguments["priority"]) if arguments.get("priority") else None),
            owner_agent_id=(str(arguments["owner_agent_id"]) if arguments.get("owner_agent_id") else None),
        )

    return run


def builtin_project_tools(projects: ProjectService) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="project_create",
            description="Create a project.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "workspace_root": {"type": "string"},
                    "description": {"type": "string"},
                    "project_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_project_create_factory(projects),
        ),
        ToolDefinition(
            name="project_list",
            description="List projects.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            risk_level="low",
            action_type="read",
            execute=_project_list_factory(projects),
        ),
        ToolDefinition(
            name="task_create",
            description="Create a task.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                    "owner_agent_id": {"type": "string"},
                },
                "required": ["project_id", "title"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_task_create_factory(projects),
        ),
        ToolDefinition(
            name="task_list",
            description="List tasks.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_task_list_factory(projects),
        ),
        ToolDefinition(
            name="task_update",
            description="Update task fields.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                    "owner_agent_id": {"type": "string"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_task_update_factory(projects),
        ),
    ]
