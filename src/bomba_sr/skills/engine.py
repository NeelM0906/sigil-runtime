from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from bomba_sr.skills.registry import SkillRecord, SkillRegistry


ToolInvoker = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class SkillExecutionResult:
    execution_id: str
    status: str
    output: dict[str, Any] | None
    tool_calls: list[dict[str, Any]]
    error_detail: str | None
    duration_ms: int


class SkillEngine:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def execute(
        self,
        tenant_id: str,
        skill_id: str,
        inputs: dict[str, Any],
        session_id: str | None = None,
        turn_id: str | None = None,
        tool_invoker: ToolInvoker | None = None,
    ) -> SkillExecutionResult:
        skill = self.registry.get_skill(tenant_id=tenant_id, skill_id=skill_id)
        if skill.status != "active":
            raise ValueError(f"skill is not active: {skill_id}@{skill.version}")

        start = time.time()
        execution_id = self.registry.create_execution(
            tenant_id=tenant_id,
            skill_id=skill.skill_id,
            skill_version=skill.version,
            session_id=session_id,
            turn_id=turn_id,
            inputs=inputs,
        )

        try:
            output, tool_calls = self._run_skill(skill, inputs, tool_invoker)
            duration_ms = int((time.time() - start) * 1000)
            self.registry.complete_execution(
                execution_id=execution_id,
                status="completed",
                output=output,
                tool_calls=tool_calls,
                error_detail=None,
                duration_ms=duration_ms,
            )
            return SkillExecutionResult(
                execution_id=execution_id,
                status="completed",
                output=output,
                tool_calls=tool_calls,
                error_detail=None,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            self.registry.complete_execution(
                execution_id=execution_id,
                status="failed",
                output=None,
                tool_calls=[],
                error_detail=str(exc),
                duration_ms=duration_ms,
            )
            return SkillExecutionResult(
                execution_id=execution_id,
                status="failed",
                output=None,
                tool_calls=[],
                error_detail=str(exc),
                duration_ms=duration_ms,
            )

    def _run_skill(
        self,
        skill: SkillRecord,
        inputs: dict[str, Any],
        tool_invoker: ToolInvoker | None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        entry = skill.manifest.get("entrypoint") or {}
        entry_type = str(entry.get("type") or "")

        if entry_type == "template":
            template = str(entry.get("template") or "")
            rendered = self._render_template(template, inputs)
            return {"text": rendered}, []

        if entry_type == "skill_doc":
            body = str(entry.get("body_text") or "")
            source_path = entry.get("source_path")
            if not body and isinstance(source_path, str) and source_path:
                body = self._load_skill_doc_body(source_path)
            return {"text": body}, []

        if entry_type == "tool_chain":
            if tool_invoker is None:
                raise ValueError("tool_invoker required for tool_chain skill")
            steps = entry.get("steps") or []
            if not isinstance(steps, list):
                raise ValueError("tool_chain steps must be list")
            calls: list[dict[str, Any]] = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                tool_name = str(step.get("tool") or "")
                if not tool_name:
                    continue
                raw_args = step.get("arguments") or {}
                if not isinstance(raw_args, dict):
                    raw_args = {}
                arguments = self._render_structure(raw_args, inputs)
                outcome = tool_invoker(tool_name, arguments)
                calls.append({"tool": tool_name, "arguments": arguments, "outcome": outcome})
            return {"tool_chain_calls": len(calls)}, calls

        if entry_type == "python_callable":
            raise ValueError("python_callable entrypoint is disabled in this runtime")

        raise ValueError(f"unsupported skill entrypoint type: {entry_type}")

    @staticmethod
    def _render_template(template: str, values: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            value = values.get(key)
            if value is None:
                return ""
            return str(value)

        return re.sub(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}", replace, template)

    @classmethod
    def _render_structure(cls, payload: Any, values: dict[str, Any]) -> Any:
        if isinstance(payload, str):
            return cls._render_template(payload, values)
        if isinstance(payload, list):
            return [cls._render_structure(x, values) for x in payload]
        if isinstance(payload, dict):
            return {k: cls._render_structure(v, values) for k, v in payload.items()}
        return payload

    @staticmethod
    def _load_skill_doc_body(source_path: str) -> str:
        content = Path(source_path).read_text(encoding="utf-8")
        match = re.match(r"^\s*---\s*\n.*?\n---\s*\n?(.*)$", content, re.DOTALL)
        if match is None:
            return content.strip()
        return match.group(1).strip()
