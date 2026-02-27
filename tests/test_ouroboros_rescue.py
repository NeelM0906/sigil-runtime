from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bomba_sr.runtime.rescue import WorkspaceRescue


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class OuroborosRescueTests(unittest.TestCase):
    def test_non_git_workspace_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rescue = WorkspaceRescue(root)
            out = rescue.snapshot()
            self.assertEqual(out["method"], "none")
            self.assertEqual(out["reason"], "not_a_git_repo")

    def test_git_snapshot_and_cleanup_ref(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(_run(["git", "init"], root).returncode, 0)
            _run(["git", "config", "user.email", "test@example.com"], root)
            _run(["git", "config", "user.name", "Tester"], root)
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            _run(["git", "add", "a.txt"], root)
            self.assertEqual(_run(["git", "commit", "-m", "init"], root).returncode, 0)

            # Uncommitted changes so stash create returns a SHA.
            (root / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
            rescue = WorkspaceRescue(root)
            snap = rescue.snapshot()
            self.assertEqual(snap["method"], "git_stash_create")
            self.assertTrue(str(snap.get("sha", "")).strip())

            ref_check = _run(["git", "show-ref", "refs/bomba/rescue"], root)
            self.assertEqual(ref_check.returncode, 0)

            rescue.cleanup_ref()
            ref_check_after = _run(["git", "show-ref", "refs/bomba/rescue"], root)
            self.assertNotEqual(ref_check_after.returncode, 0)


if __name__ == "__main__":
    unittest.main()
