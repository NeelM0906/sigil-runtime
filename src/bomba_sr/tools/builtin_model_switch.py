from __future__ import annotations

from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


def builtin_model_switch_tools() -> list[ToolDefinition]:
    def switch_model(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        state = context.loop_state_ref
        if state is None:
            raise ValueError("loop_state_unavailable")

        new_model = str(arguments.get("model_id") or "").strip()
        if not new_model:
            raise ValueError("model_id is required")
        previous = str(getattr(state, "current_model_id", ""))
        setattr(state, "current_model_id", new_model)
        return {
            "switched": True,
            "previous_model": previous,
            "new_model": new_model,
            "reason": str(arguments.get("reason") or ""),
        }

    return [
        ToolDefinition(
            name="switch_model",
            description="Switch the active model used by the loop for next iterations.",
            parameters={
                "type": "object",
                "properties": {
                    "model_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["model_id"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=switch_model,
        )
    ]
