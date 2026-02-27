from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "import_sai_identity.py"
    spec = importlib.util.spec_from_file_location("import_sai_identity", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load import_sai_identity module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImportSaiIdentityTests(unittest.TestCase):
    def test_copy_memory_skips_symlink(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            source_memory = source_dir / "memory"
            source_memory.mkdir(parents=True)
            dest_dir = root / "dest"
            (source_memory / "note.md").write_text("safe", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            (source_memory / "leak.md").symlink_to(outside)

            result = module.copy_memory_markdown_files(source_dir=source_dir, dest_dir=dest_dir, dry_run=False)
            self.assertEqual(result["copied"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertTrue((dest_dir / "memory" / "note.md").exists())
            self.assertFalse((dest_dir / "memory" / "leak.md").exists())


if __name__ == "__main__":
    unittest.main()
