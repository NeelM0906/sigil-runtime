from __future__ import annotations

import json
import itertools
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bomba_sr.codeintel.base import CodeIntelligenceAdapter, CodeIntelError
from bomba_sr.runtime.config import SerenaPolicy
from bomba_sr.runtime.tenancy import TenantContext, TenantRegistry


class SerenaUnavailableError(CodeIntelError):
    pass


class SerenaTransport(Protocol):
    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def health(self) -> bool:
        raise NotImplementedError


@dataclass
class SerenaHttpTransport:
    base_url: str
    api_key: str | None = None
    timeout_seconds: int = 20
    _req_counter: Any = itertools.count(1)
    _mcp_session_id: str | None = None
    _mcp_initialized: bool = False

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        # Preferred path: MCP streamable-http endpoint.
        mcp_error: Exception | None = None
        try:
            return self._mcp_call_tool(tool_name, arguments)
        except Exception as exc:
            mcp_error = exc

        # Backward-compatible fallback for non-MCP bridges.
        payload = {"tool": tool_name, "arguments": arguments}
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{self.base_url.rstrip('/')}/tool",
            data=body,
            method="POST",
            headers=self._headers(),
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                alt = Request(
                    url=f"{self.base_url.rstrip('/')}/tools/{tool_name}",
                    data=json.dumps(arguments).encode("utf-8"),
                    method="POST",
                    headers=self._headers(),
                )
                try:
                    with urlopen(alt, timeout=self.timeout_seconds) as response:
                        return json.loads(response.read().decode("utf-8"))
                except (HTTPError, URLError) as alt_exc:
                    raise SerenaUnavailableError(
                        f"Serena tool call failed via MCP ({mcp_error}) and legacy endpoints ({alt_exc})"
                    ) from alt_exc
            raise SerenaUnavailableError(f"Serena HTTP error ({exc.code}): {exc.reason}") from exc
        except URLError as exc:
            raise SerenaUnavailableError(f"Serena unreachable: {exc}") from exc

    def health(self) -> bool:
        # First try MCP tools/list.
        try:
            self._ensure_mcp_initialized()
            self._mcp_request("tools/list", {})
            return True
        except Exception:
            pass

        request = Request(url=f"{self.base_url.rstrip('/')}/health", method="GET", headers=self._headers())
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return 200 <= response.status < 300
        except (HTTPError, URLError):
            return False

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "mcp-protocol-version": "2025-03-26",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self._mcp_session_id:
            headers["mcp-session-id"] = self._mcp_session_id
        return headers

    def _mcp_call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._ensure_mcp_initialized()
        result = self._mcp_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        if not isinstance(result, dict):
            raise SerenaUnavailableError("Invalid MCP tools/call result type")

        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str):
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        return {"text": text}
        return result

    def _mcp_request(self, method: str, params: dict[str, Any] | None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._req_counter),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        req = Request(
            url=f"{self.base_url.rstrip('/')}/mcp",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=self._headers(),
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                response_session = response.headers.get("mcp-session-id")
                if response_session:
                    self._mcp_session_id = response_session
        except (HTTPError, URLError) as exc:
            raise SerenaUnavailableError(f"MCP request failed for {method}: {exc}") from exc

        body = self._parse_mcp_response(raw)
        if "error" in body:
            raise SerenaUnavailableError(f"MCP error for {method}: {body['error']}")
        return body.get("result")

    def _ensure_mcp_initialized(self) -> None:
        if self._mcp_initialized:
            return
        self._mcp_request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "bomba-sr-runtime",
                    "version": "0.1.0",
                },
            },
        )
        self._mcp_initialized = True

    @staticmethod
    def _parse_mcp_response(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if not text:
            raise SerenaUnavailableError("Empty MCP response body")

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Streamable HTTP may return SSE frames. Parse first JSON data payload.
        data_payloads: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_payloads.append(line[len("data:") :].strip())
        for payload in data_payloads:
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        raise SerenaUnavailableError("Unable to parse MCP response (JSON or SSE JSON payload not found)")


class SerenaCodeIntelAdapter(CodeIntelligenceAdapter):
    def __init__(
        self,
        policy: SerenaPolicy,
        tenant_registry: TenantRegistry,
        transport: SerenaTransport | None = None,
    ) -> None:
        super().__init__(policy=policy, tenant_registry=tenant_registry)
        self.transport = transport or SerenaHttpTransport(base_url=policy.base_url, api_key=policy.api_key)

    @property
    def backend_name(self) -> str:
        return "serena"

    def is_available(self) -> bool:
        if not self.policy.enabled:
            return False
        return self.transport.health()

    def _invoke_impl(self, tenant: TenantContext, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.policy.enabled:
            raise SerenaUnavailableError("Serena adapter is disabled by policy")
        payload = self.transport.call_tool(tool_name, arguments)
        if not isinstance(payload, dict):
            raise SerenaUnavailableError("Serena returned non-object payload")
        payload.setdefault("tenant_id", tenant.tenant_id)
        payload.setdefault("backend", "serena")
        return payload
