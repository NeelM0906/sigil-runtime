from __future__ import annotations

from typing import Any, Callable

from bomba_sr.codeintel.router import CodeIntelRouter
from bomba_sr.runtime.tenancy import TenantContext
from bomba_sr.search.agentic_search import AgenticSearchExecutor, SearchPlan
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _code_search_factory(search: AgenticSearchExecutor) -> Callable[[dict[str, Any], ToolContext], dict[str, Any]]:
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        scope = arguments.get("scope")
        if not isinstance(scope, list) or not scope:
            scope = ["."]
        plan = SearchPlan(
            query=query,
            intent="targeted_lookup",
            scope=[str(x) for x in scope],
            file_types=["py", "ts", "js", "md", "sql", "json"],
            escalation_allowed=True,
            escalation_mode="balanced",
        )
        pack = search.execute(plan)
        return {
            "query": query,
            "avg_confidence": pack.avg_confidence,
            "results": [
                {
                    "path": hit.path,
                    "line_start": hit.line_start,
                    "line_end": hit.line_end,
                    "snippet": hit.snippet,
                    "confidence": hit.confidence,
                }
                for hit in pack.results
            ],
        }

    return run


def _codeintel_tool_factory(
    tool_name: str,
    codeintel: CodeIntelRouter,
    tenant_context: TenantContext,
) -> Callable[[dict[str, Any], ToolContext], dict[str, Any]]:
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        outcome = codeintel.invoke(tenant_context, tool_name, arguments)
        payload = dict(outcome.payload)
        payload.setdefault("backend", outcome.backend)
        payload.setdefault("tool_name", outcome.tool_name)
        return payload

    return run


def builtin_search_tools(
    search: AgenticSearchExecutor,
    codeintel: CodeIntelRouter,
    tenant_context: TenantContext,
) -> list[ToolDefinition]:
    tools = [
        ToolDefinition(
            name="code_search",
            description="Search the local codebase for relevant snippets.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "scope": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_code_search_factory(search),
        )
    ]

    codeintel_specs = [
        ("get_symbols_overview", "Get symbol overview for a file.", "low", "read"),
        ("find_symbol", "Find symbol definitions and occurrences.", "low", "read"),
        ("find_referencing_symbols", "Find symbol references.", "low", "read"),
        ("replace_symbol_body", "Replace body of a symbol by line range.", "medium", "write"),
        ("insert_before_symbol", "Insert text before a symbol line.", "medium", "write"),
        ("insert_after_symbol", "Insert text after a symbol line.", "medium", "write"),
        ("rename_symbol", "Rename a symbol in the workspace.", "high", "write"),
    ]
    for tool_name, description, risk, action in codeintel_specs:
        tools.append(
            ToolDefinition(
                name=tool_name,
                description=description,
                parameters={"type": "object", "properties": {}, "additionalProperties": True},
                risk_level=risk,
                action_type=action,
                execute=_codeintel_tool_factory(tool_name, codeintel, tenant_context),
            )
        )
    return tools
