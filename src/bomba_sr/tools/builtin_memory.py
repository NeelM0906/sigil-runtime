from __future__ import annotations

from typing import Any

from bomba_sr.memory.hybrid import HybridMemoryStore, resolve_being_id
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _memory_search_factory(memory: HybridMemoryStore):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = int(arguments.get("limit") or 10)
        return memory.recall(user_id=context.user_id, query=query, limit=limit)

    return run


def _memory_get_factory(memory: HybridMemoryStore):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = int(arguments.get("limit") or 10)
        return memory.recall(user_id=context.user_id, query=query, limit=limit)

    return run


def _memory_store_factory(memory: HybridMemoryStore):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        key = str(arguments.get("key") or "").strip()
        content = str(arguments.get("content") or "").strip()
        if not key or not content:
            raise ValueError("key and content are required")
        confidence = float(arguments.get("confidence") or 0.5)
        reason = str(arguments.get("reason") or "memory_store_tool")
        _being_id = resolve_being_id(context.session_id, context.user_id)
        decision = memory.learn_semantic(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            memory_key=key,
            content=content,
            confidence=confidence,
            evidence_refs=[],
            reason=reason,
            being_id=_being_id,
        )
        return {
            "update_id": decision.update_id,
            "status": decision.status,
            "confidence": decision.confidence,
            "memory_id": decision.memory_id,
        }

    return run


def builtin_memory_tools(memory: HybridMemoryStore) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="memory_search",
            description="Search stored semantic and markdown memory.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_memory_search_factory(memory),
        ),
        ToolDefinition(
            name="memory_get",
            description="Retrieve memory items relevant to a query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_memory_get_factory(memory),
        ),
        ToolDefinition(
            name="memory_store",
            description="Store semantic memory with confidence.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "content": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["key", "content"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_memory_store_factory(memory),
        ),
    ]
