from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.runtime.config import RuntimeConfig
from bomba_sr.runtime.tenancy import TenantIsolationError, TenantRegistry


class RuntimeTenancyConfigTests(unittest.TestCase):
    def test_serena_defaults_enabled_with_edit_tools(self) -> None:
        cfg = RuntimeConfig()
        self.assertTrue(cfg.serena.enabled)
        self.assertTrue(cfg.serena.edit_tools_enabled)
        self.assertIn("replace_symbol_body", cfg.serena.allowed_tools)

    def test_tenant_path_guard_blocks_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = TenantRegistry(Path(td))
            tenant = registry.ensure_tenant("tenant_a")
            safe = registry.guard_path(tenant, "src/main.py")
            self.assertTrue(str(safe).startswith(str(tenant.workspace_root)))

            with self.assertRaises(TenantIsolationError):
                registry.guard_path(tenant, "../outside.txt")


if __name__ == "__main__":
    unittest.main()
