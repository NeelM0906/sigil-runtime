from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bomba_sr.plugins.registry import PluginRegistry


class PluginManifestTests(unittest.TestCase):
    def test_valid_manifest_parses(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bomba.plugin.json"
            path.write_text(
                json.dumps(
                    {
                        "plugin_id": "demo",
                        "entry_module": "demo.module",
                        "name": "Demo",
                        "version": "1.2.3",
                        "skills_dir": "skills",
                    }
                ),
                encoding="utf-8",
            )
            manifest = PluginRegistry._read_manifest(path)
            self.assertEqual(manifest.plugin_id, "demo")
            self.assertEqual(manifest.entry_module, "demo.module")
            self.assertEqual(manifest.skills_dir, "skills")

    def test_manifest_missing_fields_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bomba.plugin.json"
            path.write_text(json.dumps({"name": "missing"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                PluginRegistry._read_manifest(path)


if __name__ == "__main__":
    unittest.main()
