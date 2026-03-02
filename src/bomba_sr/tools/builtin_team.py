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
        edge_type = str(arguments.get("edge_type") or "dependency").strip()
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
    ]
