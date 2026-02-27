from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bomba_sr.codeintel.base import CodeIntelligenceAdapter, ToolOutcome
from bomba_sr.codeintel.native import NativeCodeIntelAdapter
from bomba_sr.codeintel.serena import SerenaCodeIntelAdapter, SerenaTransport, SerenaUnavailableError
from bomba_sr.runtime.config import RuntimeConfig
from bomba_sr.runtime.tenancy import TenantContext, TenantRegistry


@dataclass
class CodeIntelRouter:
    config: RuntimeConfig
    tenant_registry: TenantRegistry
    serena_transport: SerenaTransport | None = None

    def __post_init__(self) -> None:
        self._native = NativeCodeIntelAdapter(policy=self.config.serena, tenant_registry=self.tenant_registry)
        self._serena = SerenaCodeIntelAdapter(
            policy=self.config.serena,
            tenant_registry=self.tenant_registry,
            transport=self.serena_transport,
        )

    @property
    def default_backend(self) -> str:
        return "serena" if self.config.serena.enabled else "native"

    def invoke(self, tenant: TenantContext, tool_name: str, arguments: dict[str, Any]) -> ToolOutcome:
        if self.default_backend == "native":
            return self._native.invoke(tenant, tool_name, arguments)

        try:
            return self._serena.invoke(tenant, tool_name, arguments)
        except SerenaUnavailableError:
            if not self.config.serena.fallback_to_native:
                raise
            return self._native.invoke(tenant, tool_name, arguments)

    def availability(self) -> dict[str, Any]:
        return {
            "default_backend": self.default_backend,
            "serena_enabled": self.config.serena.enabled,
            "serena_edit_tools_enabled": self.config.serena.edit_tools_enabled,
            "serena_available": self._serena.is_available() if self.config.serena.enabled else False,
            "native_available": self._native.is_available(),
            "fallback_to_native": self.config.serena.fallback_to_native,
        }
