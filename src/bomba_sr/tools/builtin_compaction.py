from __future__ import annotations

import json
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMProvider
from bomba_sr.tools.base import ToolContext, ToolDefinition


COMPACTION_PROMPT = (
    "Summarize the following conversation into key facts, decisions made, and pending tasks. "
    "Preserve all tool results and their outcomes. Be concise but complete."
)
COMPACTION_MAX_CHARS = 8000


def _render_message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return json.dumps(message, ensure_ascii=True)
    return str(message)


def builtin_compaction_tools(
    provider: LLMProvider,
    default_model_id: str,
    compaction_model_id: str | None = None,
) -> list[ToolDefinition]:
    def compact_context(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        state = context.loop_state_ref
        if state is None:
            raise ValueError("loop_state_unavailable")
        if len(state.messages) < 6:
            return {"compacted": False, "reason": "conversation_too_short"}

        conversation_dump = []
        for msg in state.messages:
            conversation_dump.append(f"{msg.role}: {_render_message_text(msg.content)}")
        transcript = "\n\n".join(conversation_dump)

        model_to_use = compaction_model_id or str(getattr(state, "current_model_id", "") or default_model_id)
        response = provider.generate(
            model=model_to_use,
            messages=[
                ChatMessage(role="system", content=COMPACTION_PROMPT),
                ChatMessage(role="user", content=transcript),
            ],
        )
        summary = (response.text or "").strip()
        if len(summary) > COMPACTION_MAX_CHARS:
            summary = summary[:COMPACTION_MAX_CHARS]

        original_messages = len(state.messages)
        system_message = state.messages[0] if state.messages and state.messages[0].role == "system" else ChatMessage(
            role="system",
            content="You are BOMBA SR runtime assistant.",
        )
        tail = [m for m in state.messages[1:] if m.role != "system"][-4:]
        summary_message = ChatMessage(role="user", content=f"<compacted_history>\n{summary}\n</compacted_history>")
        state.messages = [system_message, summary_message, *tail]

        return {
            "compacted": True,
            "original_messages": original_messages,
            "compacted_messages": len(state.messages),
            "summary": summary,
            "reason": str(arguments.get("reason") or ""),
            "model_used": model_to_use,
        }

    return [
        ToolDefinition(
            name="compact_context",
            description="Compact long conversation state into a concise summary and preserve recent exchanges.",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": ["reason"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=compact_context,
        )
    ]
