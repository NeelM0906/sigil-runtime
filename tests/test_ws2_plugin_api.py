from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.plugins.api import PluginAPI


class _FakeRegistry:
    def __init__(self) -> None:
        self.tools: list[tuple[str, object]] = []
        self.skill_dirs: list[tuple[str, Path]] = []

    def _register_plugin_tool(self, plugin_id: str, tool: object) -> None:
        self.tools.append((plugin_id, tool))

    def _register_plugin_skill_dir(self, plugin_id: str, path: Path) -> None:
        self.skill_dirs.append((plugin_id, path))


class PluginAPITests(unittest.TestCase):
    def test_register_tool_and_skill_dir(self) -> None:
        registry = _FakeRegistry()
        api = PluginAPI(plugin_id="demo", registry=registry, config={"enabled": True})
        api.register_tool({"name": "tool-a"})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "skills"
            path.mkdir(parents=True, exist_ok=True)
            api.register_skill_dir(path)

        self.assertEqual(registry.tools, [("demo", {"name": "tool-a"})])
        self.assertEqual(len(registry.skill_dirs), 1)
        self.assertEqual(registry.skill_dirs[0][0], "demo")
        self.assertEqual(registry.skill_dirs[0][1].name, "skills")


if __name__ == "__main__":
    unittest.main()
