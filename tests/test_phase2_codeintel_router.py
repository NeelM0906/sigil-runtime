from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.codeintel.router import CodeIntelRouter
from bomba_sr.codeintel.serena import SerenaUnavailableError
from bomba_sr.runtime.config import RuntimeConfig, SerenaPolicy
from bomba_sr.runtime.tenancy import TenantRegistry


class _FakeSerenaTransport:
    def __init__(self, available: bool = True):
        self.available = available
        self.calls: list[tuple[str, dict]] = []

    def health(self) -> bool:
        return self.available

    def call_tool(self, tool_name: str, arguments: dict):
        if not self.available:
            raise SerenaUnavailableError("offline")
        self.calls.append((tool_name, arguments))
        return {
            "tool": tool_name,
            "arguments": arguments,
            "file_path": arguments.get("file_path", ""),
        }


class CodeIntelRouterTests(unittest.TestCase):
    def test_serena_default_and_edit_tool_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = TenantRegistry(Path(td))
            tenant = registry.ensure_tenant("tenant_b")
            file_path = tenant.workspace_root / "main.py"
            file_path.write_text("def hello():\n    return 'x'\n", encoding="utf-8")

            cfg = RuntimeConfig(serena=SerenaPolicy(enabled=True, edit_tools_enabled=True, fallback_to_native=False))
            transport = _FakeSerenaTransport(available=True)
            router = CodeIntelRouter(cfg, registry, serena_transport=transport)

            outcome = router.invoke(
                tenant,
                "replace_symbol_body",
                {
                    "file_path": str(file_path),
                    "start_line": 1,
                    "end_line": 2,
                    "new_body": "def hello():\n    return 'y'",
                },
            )
            self.assertEqual(outcome.backend, "serena")
            self.assertEqual(outcome.tool_name, "replace_symbol_body")
            self.assertEqual(len(transport.calls), 1)

    def test_fallback_to_native_when_serena_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = TenantRegistry(Path(td))
            tenant = registry.ensure_tenant("tenant_c")
            file_path = tenant.workspace_root / "sample.py"
            file_path.write_text("def demo():\n    return 1\n", encoding="utf-8")

            cfg = RuntimeConfig(serena=SerenaPolicy(enabled=True, edit_tools_enabled=True, fallback_to_native=True))
            router = CodeIntelRouter(cfg, registry, serena_transport=_FakeSerenaTransport(available=False))

            outcome = router.invoke(
                tenant,
                "replace_symbol_body",
                {
                    "file_path": str(file_path),
                    "start_line": 1,
                    "end_line": 2,
                    "new_body": "def demo():\n    return 2",
                },
            )
            self.assertEqual(outcome.backend, "native")
            updated = file_path.read_text(encoding="utf-8")
            self.assertIn("return 2", updated)


if __name__ == "__main__":
    unittest.main()
