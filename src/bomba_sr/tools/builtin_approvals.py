from __future__ import annotations

from typing import Any

from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.memory.hybrid import HybridMemoryStore
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _list_approvals_factory(governance: ToolGovernanceService, memory: HybridMemoryStore):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        approval_type = str(arguments.get("type") or "all").lower()
        rows: list[dict[str, Any]] = []

        if approval_type in {"all", "tool"}:
            for item in governance.list_pending_approvals(context.tenant_id):
                rows.append(
                    {
                        "id": f"tool:{item['approval_id']}",
                        "kind": "tool",
                        "status": item.get("status"),
                        "risk": item.get("risk_class"),
                        "action": item.get("action_type"),
                        "confidence": item.get("confidence"),
                        "reason": item.get("reason"),
                        "requested_at": item.get("requested_at"),
                    }
                )

        if approval_type in {"all", "learning"}:
            for item in memory.pending_approvals(context.tenant_id, context.user_id):
                rows.append(
                    {
                        "id": f"learning:{item['update_id']}",
                        "kind": "learning",
                        "status": "pending",
                        "risk": "medium",
                        "action": "memory_store",
                        "confidence": item.get("confidence"),
                        "reason": item.get("reason"),
                        "requested_at": item.get("created_at"),
                        "memory_key": item.get("memory_key"),
                    }
                )

        return {"approvals": rows}

    return run


def _decide_approval_factory(governance: ToolGovernanceService, memory: HybridMemoryStore):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        approval_id = str(arguments.get("approval_id") or "").strip()
        approved = bool(arguments.get("approved"))
        if not approval_id:
            raise ValueError("approval_id is required")

        if approval_id.startswith("tool:"):
            raw_id = approval_id.split(":", 1)[1]
            updated = governance.decide_approval(
                tenant_id=context.tenant_id,
                approval_id=raw_id,
                approved=approved,
                decided_by="model",
            )
            return {"kind": "tool", "result": updated}

        if approval_id.startswith("learning:"):
            raw_id = approval_id.split(":", 1)[1]
            updated = memory.approve_learning(raw_id, approved=approved)
            return {
                "kind": "learning",
                "result": {
                    "update_id": updated.update_id,
                    "status": updated.status,
                    "confidence": updated.confidence,
                    "memory_id": updated.memory_id,
                },
            }

        # Backward compatibility: attempt tool approval id first, then learning id.
        try:
            updated = governance.decide_approval(
                tenant_id=context.tenant_id,
                approval_id=approval_id,
                approved=approved,
                decided_by="model",
            )
            return {"kind": "tool", "result": updated}
        except Exception:
            updated = memory.approve_learning(approval_id, approved=approved)
            return {
                "kind": "learning",
                "result": {
                    "update_id": updated.update_id,
                    "status": updated.status,
                    "confidence": updated.confidence,
                    "memory_id": updated.memory_id,
                },
            }

    return run


def builtin_approval_tools(governance: ToolGovernanceService, memory: HybridMemoryStore) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="list_approvals",
            description="List pending tool and learning approvals.",
            parameters={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["all", "tool", "learning"]},
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_approvals_factory(governance, memory),
        ),
        ToolDefinition(
            name="decide_approval",
            description="Approve or reject a pending approval item.",
            parameters={
                "type": "object",
                "properties": {
                    "approval_id": {"type": "string"},
                    "approved": {"type": "boolean"},
                },
                "required": ["approval_id", "approved"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="write",
            execute=_decide_approval_factory(governance, memory),
        ),
    ]
