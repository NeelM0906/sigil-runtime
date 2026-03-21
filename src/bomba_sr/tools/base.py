from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ResolvedPolicy
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import resolve_alias
from bomba_sr.storage.db import RuntimeDB


ToolCallable = Callable[[dict[str, Any], "ToolContext"], dict[str, Any]]

# Parameters that are allowed to carry large content (file bodies, messages, etc.)
_LARGE_VALUE_PARAMS = frozenset({
    "content", "file_content", "body", "new_body", "text", "message",
    "message_body", "instructions", "prompt", "data", "payload",
})
_MAX_PARAM_VALUE_LEN = 500


def truncate_output(output: dict[str, Any], max_chars: int = 15000) -> dict[str, Any]:
    """Truncate oversized top-level string values in a tool output dict."""
    if max_chars < 1:
        return dict(output)
    result: dict[str, Any] = {}
    for key, value in output.items():
        if isinstance(value, str) and len(value) > max_chars:
            half = max_chars // 2
            omitted = len(value) - max_chars
            result[key] = (
                value[:half]
                + f"\n\n... [{omitted} chars truncated] ...\n\n"
                + value[-half:]
            )
        else:
            result[key] = value
    return result


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    risk_level: str
    action_type: str
    execute: ToolCallable
    aliases: tuple[str, ...] = ()


@dataclass
class ToolContext:
    tenant_id: str
    session_id: str
    turn_id: str
    user_id: str
    workspace_root: Path
    db: RuntimeDB
    guard_path: Callable[[str | Path], Path]
    loop_state_ref: Any | None = None


@dataclass(frozen=True)
class ToolCallResult:
    tool_call_id: str
    tool_name: str
    status: str
    output: dict[str, Any]
    risk_class: str
    duration_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "output": self.output,
            "risk_class": self.risk_class,
            "duration_ms": self.duration_ms,
        }


class ToolExecutor:
    def __init__(
        self,
        governance: ToolGovernanceService,
        pipeline: PolicyPipeline,
        tool_result_max_chars: int = 15000,
    ):
        self.governance = governance
        self.pipeline = pipeline
        self._tool_result_max_chars = max(1, int(tool_result_max_chars))
        self._tools: dict[str, ToolDefinition] = {}
        self._alias_index: dict[str, str] = {}

    def register(self, tool: ToolDefinition) -> None:
        canonical = resolve_alias(tool.name)
        if canonical in self._tools:
            raise ValueError(f"tool already registered: {canonical}")
        self._tools[canonical] = tool
        self._alias_index[canonical] = canonical
        for alias in tool.aliases:
            self._alias_index[resolve_alias(alias)] = canonical
        self.governance.register_classification(canonical, tool.action_type, tool.risk_level)

    def register_many(self, tools: list[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def known_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def resolve_name(self, tool_name: str) -> str:
        canonical = resolve_alias(tool_name)
        return self._alias_index.get(canonical, canonical)

    def get_action_type(self, tool_name: str) -> str:
        canonical = self.resolve_name(tool_name)
        tool = self._tools.get(canonical)
        return tool.action_type if tool is not None else "unknown"

    def available_tool_schemas(self, policy: ResolvedPolicy, format: str = "openai") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name, tool in sorted(self._tools.items()):
            if not self.pipeline.is_tool_allowed(name, policy):
                continue
            out.append(self._format_tool_schema(name=name, tool=tool, format=format))
        return out

    def available_tool_schemas_with_overrides(
        self,
        policy: ResolvedPolicy,
        overrides: set[str],
        format: str = "openai",
    ) -> list[dict[str, Any]]:
        normalized_overrides = {self.resolve_name(name) for name in overrides}
        out: list[dict[str, Any]] = []
        for name, tool in sorted(self._tools.items()):
            allowed = self.pipeline.is_tool_allowed(name, policy)
            is_override = name in normalized_overrides
            if not allowed and not is_override:
                continue
            if name in policy.denied_tools:
                continue
            out.append(self._format_tool_schema(name=name, tool=tool, format=format))
        return out

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolContext,
        policy: ResolvedPolicy,
        confidence: float = 1.0,
        tool_call_id: str | None = None,
    ) -> ToolCallResult:
        call_id = tool_call_id or f"call-{int(time.time() * 1000)}"
        canonical = self.resolve_name(tool_name)
        if canonical not in self._tools:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="error",
                output={"error": f"unknown_tool:{canonical}"},
                risk_class="unknown",
                duration_ms=0,
            )

        if not self.pipeline.is_tool_allowed(canonical, policy):
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="denied",
                output={"error": "policy_denied"},
                risk_class="unknown",
                duration_ms=0,
            )

        action_type, risk_class = self.governance.classify_tool(canonical)
        decision = self.governance.evaluate(
            tenant_id=context.tenant_id,
            action_type=action_type,
            risk_class=risk_class,
            confidence=confidence,
            payload={"tool_name": canonical, "arguments": arguments},
            session_id=context.session_id,
            turn_id=context.turn_id,
        )
        if decision.requires_approval:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="approval_required",
                output={"approval_id": decision.approval_id, "reason": decision.reason},
                risk_class=risk_class,
                duration_ms=0,
            )
        if not decision.allowed:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="denied",
                output={"reason": decision.reason},
                risk_class=risk_class,
                duration_ms=0,
            )

        # Guard: reject mega-strings in non-content parameters.
        violations = []
        for param_name, param_val in arguments.items():
            if param_name in _LARGE_VALUE_PARAMS:
                continue
            if isinstance(param_val, str) and len(param_val) > _MAX_PARAM_VALUE_LEN:
                violations.append(
                    f"{param_name}: {len(param_val)} chars (max {_MAX_PARAM_VALUE_LEN})"
                )
        if violations:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="error",
                output={
                    "error": (
                        f"Parameter value too long for tool '{canonical}'. "
                        f"Search/identifier parameters must be under {_MAX_PARAM_VALUE_LEN} chars. "
                        f"Violations: {'; '.join(violations)}"
                    ),
                },
                risk_class=risk_class,
                duration_ms=0,
            )

        start = time.time()
        tool = self._tools[canonical]
        try:
            payload = tool.execute(arguments, context)
        except Exception as exc:
            result = ToolCallResult(
                tool_call_id=call_id,
                tool_name=canonical,
                status="error",
                output={"error": str(exc)},
                risk_class=risk_class,
                duration_ms=int((time.time() - start) * 1000),
            )
            self._audit_log(context, canonical, arguments, result)
            return result

        result = ToolCallResult(
            tool_call_id=call_id,
            tool_name=canonical,
            status="executed",
            output=truncate_output(
                payload if isinstance(payload, dict) else {"result": json.dumps(payload)},
                max_chars=self._tool_result_max_chars,
            ),
            risk_class=risk_class,
            duration_ms=int((time.time() - start) * 1000),
        )
        self._audit_log(context, canonical, arguments, result)
        return result

    def _audit_log(
        self,
        context: ToolContext,
        tool_name: str,
        arguments: dict[str, Any],
        result: ToolCallResult,
    ) -> None:
        """Write a row to tool_audit_log. Must never cause a tool call to fail."""
        try:
            import uuid
            from datetime import datetime, timezone
            args_summary = json.dumps(arguments, default=str)[:500]
            context.db.execute_commit(
                "INSERT INTO tool_audit_log "
                "(id, tenant_id, being_id, user_id, session_id, tool_name, "
                "arguments_summary, result_status, error_message, duration_ms, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    context.tenant_id,
                    None,  # being_id resolved from session pattern if needed
                    context.user_id,
                    context.session_id,
                    tool_name,
                    args_summary,
                    result.status,
                    str(result.output.get("error")) if result.status == "error" else None,
                    result.duration_ms,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception:
            pass  # Audit logging must never break tool execution

    @staticmethod
    def _format_tool_schema(name: str, tool: ToolDefinition, format: str) -> dict[str, Any]:
        if format == "anthropic":
            return {
                "name": name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
