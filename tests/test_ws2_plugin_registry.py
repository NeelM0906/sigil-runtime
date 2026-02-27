from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bomba_sr.plugins.registry import PluginRegistry


def _write_plugin(root: Path, plugin_id: str, module_name: str = "plugin_main.py") -> Path:
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "skills").mkdir(parents=True, exist_ok=True)
    (plugin_dir / module_name).write_text(
        "from pathlib import Path\n"
        "def register(api):\n"
        "    api.register_tool({'plugin': api.plugin_id, 'name': 'demo_tool'})\n"
        "    api.register_skill_dir(Path(__file__).parent / 'skills')\n",
        encoding="utf-8",
    )
    (plugin_dir / "bomba.plugin.json").write_text(
        json.dumps(
            {
                "plugin_id": plugin_id,
                "name": plugin_id,
                "version": "0.1.0",
                "entry_module": module_name,
                "skills_dir": "skills",
            }
        ),
        encoding="utf-8",
    )
    return plugin_dir


class PluginRegistryTests(unittest.TestCase):
    def test_discover_load_and_enable_disable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_plugin(root, "plugin_alpha")
            registry = PluginRegistry()

            manifests = registry.discover([root])
            self.assertEqual(len(manifests), 1)
            self.assertEqual(manifests[0].plugin_id, "plugin_alpha")

            registry.load(manifests[0])
            tools = registry.get_tools()
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0]["plugin"], "plugin_alpha")

            skill_dirs = registry.get_skill_dirs()
            self.assertEqual(len(skill_dirs), 2)  # manifest skills_dir + register_skill_dir
            self.assertTrue(all(path.name == "skills" for path in skill_dirs))

            registry.disable("plugin_alpha")
            self.assertEqual(registry.get_tools(), [])
            self.assertEqual(registry.get_skill_dirs(), [])

            registry.enable("plugin_alpha")
            self.assertEqual(len(registry.get_tools()), 1)

    def test_allow_and_deny_filters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_plugin(root, "plugin_allowed")
            _write_plugin(root, "plugin_blocked")

            allow_registry = PluginRegistry(allow=("plugin_allowed",))
            allow_manifests = allow_registry.discover([root])
            self.assertEqual({m.plugin_id for m in allow_manifests}, {"plugin_allowed"})

            deny_registry = PluginRegistry(deny=("plugin_blocked",))
            deny_manifests = deny_registry.discover([root])
            self.assertEqual({m.plugin_id for m in deny_manifests}, {"plugin_allowed"})


if __name__ == "__main__":
    unittest.main()
