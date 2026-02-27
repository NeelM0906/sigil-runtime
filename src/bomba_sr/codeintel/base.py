from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bomba_sr.runtime.config import SerenaPolicy
from bomba_sr.runtime.tenancy import TenantContext, TenantRegistry


EDIT_TOOL_NAMES = frozenset(
    {
        "replace_symbol_body",
        "insert_before_symbol",
        "insert_after_symbol",
        "rename_symbol",
    }
)


class CodeIntelError(RuntimeError):
    pass


class ToolPermissionError(CodeIntelError):
    pass


class ToolPathViolationError(CodeIntelError):
    pass


@dataclass(frozen=True)
class ToolOutcome:
    tool_name: str
    backend: str
    payload: dict[str, Any]


class CodeIntelligenceAdapter(ABC):
    def __init__(self, policy: SerenaPolicy, tenant_registry: TenantRegistry) -> None:
        self.policy = policy
        self.tenant_registry = tenant_registry

    @property
    @abstractmethod
    def backend_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _invoke_impl(self, tenant: TenantContext, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def invoke(self, tenant: TenantContext, tool_name: str, arguments: dict[str, Any]) -> ToolOutcome:
        self._assert_allowed(tool_name)
        guarded_arguments = self._guard_arguments(tenant, arguments)
        payload = self._invoke_impl(tenant, tool_name, guarded_arguments)
        self._assert_paths_within_workspace(tenant, payload)
        return ToolOutcome(tool_name=tool_name, backend=self.backend_name, payload=payload)

    def _assert_allowed(self, tool_name: str) -> None:
        if tool_name not in self.policy.allowed_tools:
            raise ToolPermissionError(f"Tool is not enabled by policy: {tool_name}")
        if tool_name in EDIT_TOOL_NAMES and not self.policy.edit_tools_enabled:
            raise ToolPermissionError(
                f"Edit tool is disabled by policy: {tool_name}"
            )

    def _guard_arguments(self, tenant: TenantContext, arguments: dict[str, Any]) -> dict[str, Any]:
        guarded: dict[str, Any] = {}
        for key, value in arguments.items():
            if key in {"path", "file_path", "target_path", "source_path"} and isinstance(value, str):
                guarded[key] = str(self.tenant_registry.guard_path(tenant, value))
                continue

            if key in {"scope", "paths", "file_paths"} and isinstance(value, list):
                guarded[key] = [str(self.tenant_registry.guard_path(tenant, str(item))) for item in value]
                continue

            guarded[key] = value
        return guarded

    def _assert_paths_within_workspace(self, tenant: TenantContext, payload: dict[str, Any]) -> None:
        root = tenant.workspace_root.resolve()

        def check(value: Any) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key in {"path", "file_path", "target_path", "source_path"} and isinstance(nested, str):
                        p = Path(nested).resolve()
                        if p != root and root not in p.parents:
                            raise ToolPathViolationError(
                                f"Tool result escaped workspace root: {p}"
                            )
                    check(nested)
                return

            if isinstance(value, list):
                for nested in value:
                    check(nested)

        check(payload)
