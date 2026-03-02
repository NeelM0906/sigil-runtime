from __future__ import annotations

from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


def builtin_team_tools(
    team_manager: Any,
    tenant_id: str,
) -> list[ToolDefinition]:
    """Team Manager graph tools -- gated by BOMBA_TEAM_MANAGER_ENABLED."""

    def _create_graph(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        name = str(arguments.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        return team_manager.create_graph(
            tenant_id=context.tenant_id,
            workspace_id=str(context.workspace_root),
            name=name,
            description=str(arguments.get("description", "")),
            metadata=arguments.get("metadata"),
        )

    def _list_graphs(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        items = team_manager.list_graphs(tenant_id=context.tenant_id)
        return {"graphs": items}

    def _add_node(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        kind = str(arguments.get("kind") or "").strip()
        label = str(arguments.get("label") or "").strip()
        if not graph_id:
            raise ValueError("graph_id is required")
        if not kind:
            raise ValueError("kind is required")
        return team_manager.add_node(
            tenant_id=context.tenant_id,
            graph_id=graph_id,
            kind=kind,
            label=label,
            config=arguments.get("config"),
            position_x=float(arguments.get("position_x", 0.0)),
            position_y=float(arguments.get("position_y", 0.0)),
        )

    def _list_nodes(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        if not graph_id:
            raise ValueError("graph_id is required")
        kind = arguments.get("kind")
        items = team_manager.list_nodes(tenant_id=context.tenant_id, graph_id=graph_id, kind=kind)
        return {"nodes": items}

    def _add_edge(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        source = str(arguments.get("source_node_id") or "").strip()
        target = str(arguments.get("target_node_id") or "").strip()
        edge_type = str(arguments.get("edge_type") or "feeds").strip()
        if not graph_id or not source or not target:
            raise ValueError("graph_id, source_node_id, target_node_id are required")
        return team_manager.add_edge(
            tenant_id=context.tenant_id,
            graph_id=graph_id,
            source_node_id=source,
            target_node_id=target,
            edge_type=edge_type,
            metadata=arguments.get("metadata"),
        )

    def _validate_graph(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        if not graph_id:
            raise ValueError("graph_id is required")
        return team_manager.validate_graph(tenant_id=context.tenant_id, graph_id=graph_id)

    def _set_variable(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        key = str(arguments.get("key") or "").strip()
        value = str(arguments.get("value", ""))
        var_type = str(arguments.get("var_type", "string"))
        if not graph_id or not key:
            raise ValueError("graph_id and key are required")
        return team_manager.set_variable(
            tenant_id=context.tenant_id,
            graph_id=graph_id,
            key=key,
            value=value,
            var_type=var_type,
        )

    def _save_pipeline(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        node_id = str(arguments.get("node_id") or "").strip()
        steps = arguments.get("steps") or []
        if not graph_id or not node_id:
            raise ValueError("graph_id and node_id are required")
        return team_manager.save_pipeline(
            tenant_id=context.tenant_id,
            graph_id=graph_id,
            node_id=node_id,
            steps=steps,
        )

    def _deploy_team(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        if not graph_id:
            raise ValueError("graph_id is required")
        return team_manager.build_deploy_plan(tenant_id=context.tenant_id, graph_id=graph_id)

    # ── Deploy orchestrator handlers ──

    def _deploy_start(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        if not graph_id:
            raise ValueError("graph_id is required")
        return team_manager.deploy_graph(tenant_id=context.tenant_id, graph_id=graph_id)

    def _deploy_status(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        deployment_id = str(arguments.get("deployment_id") or "").strip()
        if not deployment_id:
            raise ValueError("deployment_id is required")
        result = team_manager.get_deployment(tenant_id=context.tenant_id, deployment_id=deployment_id)
        if result is None:
            return {"error": "deployment_not_found"}
        return result

    def _deploy_list(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = arguments.get("graph_id")
        if graph_id:
            graph_id = str(graph_id).strip() or None
        items = team_manager.list_deployments(tenant_id=context.tenant_id, graph_id=graph_id)
        return {"deployments": items}

    def _deploy_cancel(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        deployment_id = str(arguments.get("deployment_id") or "").strip()
        if not deployment_id:
            raise ValueError("deployment_id is required")
        return team_manager.cancel_deployment(tenant_id=context.tenant_id, deployment_id=deployment_id)

    def _deploy_primer(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        node_id = str(arguments.get("node_id") or "").strip()
        if not graph_id or not node_id:
            raise ValueError("graph_id and node_id are required")
        return team_manager.generate_deploy_primer(
            tenant_id=context.tenant_id, graph_id=graph_id, node_id=node_id,
        )

    # ── Schedule handlers ──

    def _schedule_create(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = str(arguments.get("graph_id") or "").strip()
        name = str(arguments.get("name") or "").strip()
        cron_expression = str(arguments.get("cron_expression") or "").strip()
        if not graph_id or not name or not cron_expression:
            raise ValueError("graph_id, name, and cron_expression are required")
        return team_manager.create_schedule(
            tenant_id=context.tenant_id,
            graph_id=graph_id,
            name=name,
            cron_expression=cron_expression,
            action=str(arguments.get("action", "deploy")),
            action_params=arguments.get("action_params"),
            requires_approval=bool(arguments.get("requires_approval", False)),
        )

    def _schedule_list(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        graph_id = arguments.get("graph_id")
        if graph_id:
            graph_id = str(graph_id).strip() or None
        items = team_manager.list_schedules(tenant_id=context.tenant_id, graph_id=graph_id)
        return {"schedules": items}

    def _schedule_update(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        schedule_id = str(arguments.get("schedule_id") or "").strip()
        if not schedule_id:
            raise ValueError("schedule_id is required")
        kwargs: dict[str, Any] = {}
        for field in ("name", "cron_expression", "action", "action_params", "enabled", "requires_approval"):
            if field in arguments and arguments[field] is not None:
                kwargs[field] = arguments[field]
        return team_manager.update_schedule(
            tenant_id=context.tenant_id,
            schedule_id=schedule_id,
            **kwargs,
        )

    def _schedule_delete(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        schedule_id = str(arguments.get("schedule_id") or "").strip()
        if not schedule_id:
            raise ValueError("schedule_id is required")
        return team_manager.delete_schedule(tenant_id=context.tenant_id, schedule_id=schedule_id)

    def _schedule_toggle(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        schedule_id = str(arguments.get("schedule_id") or "").strip()
        if not schedule_id:
            raise ValueError("schedule_id is required")
        enabled = arguments.get("enabled")
        if enabled is None:
            raise ValueError("enabled is required")
        return team_manager.toggle_schedule(
            tenant_id=context.tenant_id,
            schedule_id=schedule_id,
            enabled=bool(enabled),
        )

    return [
        ToolDefinition(
            name="team_graph_create",
            description="Create a new team graph (org chart) to model agent/human/skill topology.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Graph name"},
                    "description": {"type": "string", "description": "Optional description"},
                    "metadata": {"type": "object", "description": "Optional metadata dict"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_create_graph,
        ),
        ToolDefinition(
            name="team_graph_list",
            description="List all team graphs in the current workspace.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_graphs,
        ),
        ToolDefinition(
            name="team_node_add",
            description="Add a node to a team graph. Kinds: human, group, agent, skill, pipeline, context, note.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["human", "group", "agent", "skill", "pipeline", "context", "note"]},
                    "label": {"type": "string"},
                    "config": {"type": "object"},
                    "position_x": {"type": "number"},
                    "position_y": {"type": "number"},
                },
                "required": ["graph_id", "kind"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_add_node,
        ),
        ToolDefinition(
            name="team_node_list",
            description="List nodes in a team graph, optionally filtered by kind.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["graph_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_nodes,
        ),
        ToolDefinition(
            name="team_edge_add",
            description="Add an edge between two nodes in a team graph.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "source_node_id": {"type": "string"},
                    "target_node_id": {"type": "string"},
                    "edge_type": {"type": "string", "enum": ["reports_to", "delegates_to", "feeds", "uses", "triggers", "annotates"]},
                    "metadata": {"type": "object"},
                },
                "required": ["graph_id", "source_node_id", "target_node_id", "edge_type"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_add_edge,
        ),
        ToolDefinition(
            name="team_graph_validate",
            description="Validate a team graph for structural correctness (cycle detection, edge constraints).",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                },
                "required": ["graph_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_validate_graph,
        ),
        ToolDefinition(
            name="team_variable_set",
            description="Set a graph-scoped variable (used in pipelines and deploy primers).",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "var_type": {"type": "string", "enum": ["string", "number", "boolean", "json", "secret"]},
                },
                "required": ["graph_id", "key", "value"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_set_variable,
        ),
        ToolDefinition(
            name="team_pipeline_save",
            description="Save ordered pipeline steps for a pipeline node.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["graph_id", "node_id", "steps"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_save_pipeline,
        ),
        ToolDefinition(
            name="team_deploy",
            description="Deploy a team graph -- spawns subagents for each agent node in topological order.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                },
                "required": ["graph_id"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_deploy_team,
        ),
        # ── Deploy orchestrator tools ──
        ToolDefinition(
            name="team_deploy_start",
            description="Deploy a graph: validates, builds deploy plan, and creates a deployment record.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph to deploy"},
                },
                "required": ["graph_id"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_deploy_start,
        ),
        ToolDefinition(
            name="team_deploy_status",
            description="Get the status of a deployment by ID.",
            parameters={
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                },
                "required": ["deployment_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_deploy_status,
        ),
        ToolDefinition(
            name="team_deploy_list",
            description="List deployments, optionally filtered by graph_id.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Optional graph filter"},
                },
                "required": [],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_deploy_list,
        ),
        ToolDefinition(
            name="team_deploy_cancel",
            description="Cancel a pending or running deployment.",
            parameters={
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID to cancel"},
                },
                "required": ["deployment_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_deploy_cancel,
        ),
        ToolDefinition(
            name="team_deploy_primer",
            description="Generate a deploy primer for a specific node in a graph.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph ID"},
                    "node_id": {"type": "string", "description": "Node ID to generate primer for"},
                },
                "required": ["graph_id", "node_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_deploy_primer,
        ),
        # ── Schedule tools ──
        ToolDefinition(
            name="team_schedule_create",
            description="Create a recurring schedule for a team graph (e.g. deploy every hour).",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph to schedule"},
                    "name": {"type": "string", "description": "Human-readable schedule name"},
                    "cron_expression": {"type": "string", "description": "Cron expression (e.g. '0 * * * *' for hourly)"},
                    "action": {"type": "string", "enum": ["deploy", "validate", "primer"], "description": "Action to run on schedule"},
                    "action_params": {"type": "object", "description": "Optional parameters for the action"},
                    "requires_approval": {"type": "boolean", "description": "Whether execution requires approval"},
                },
                "required": ["graph_id", "name", "cron_expression"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_schedule_create,
        ),
        ToolDefinition(
            name="team_schedule_list",
            description="List schedules, optionally filtered by graph_id.",
            parameters={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Optional graph filter"},
                },
                "required": [],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_schedule_list,
        ),
        ToolDefinition(
            name="team_schedule_update",
            description="Update a team schedule's fields (name, cron_expression, action, enabled, etc.).",
            parameters={
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "string"},
                    "name": {"type": "string"},
                    "cron_expression": {"type": "string"},
                    "action": {"type": "string", "enum": ["deploy", "validate", "primer"]},
                    "action_params": {"type": "object"},
                    "enabled": {"type": "boolean"},
                    "requires_approval": {"type": "boolean"},
                },
                "required": ["schedule_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_schedule_update,
        ),
        ToolDefinition(
            name="team_schedule_delete",
            description="Delete a team schedule.",
            parameters={
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "string"},
                },
                "required": ["schedule_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_schedule_delete,
        ),
        ToolDefinition(
            name="team_schedule_toggle",
            description="Enable or disable a team schedule.",
            parameters={
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["schedule_id", "enabled"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="write",
            execute=_schedule_toggle,
        ),
    ]
