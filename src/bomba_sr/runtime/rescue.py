from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class WorkspaceRescue:
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()
        self._stash_id: str | None = None
        self._is_git: bool = (self.workspace_root / ".git").is_dir()

    def snapshot(self) -> dict[str, Any]:
        """Take a pre-execution snapshot. Uses git stash create when available."""
        if not self._is_git:
            return {"method": "none", "reason": "not_a_git_repo"}
        result = subprocess.run(
            ["git", "stash", "create", "bomba-rescue-point"],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        stash_sha = result.stdout.strip()
        if stash_sha:
            self._stash_id = stash_sha
            subprocess.run(
                ["git", "update-ref", "refs/bomba/rescue", stash_sha],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
            return {"method": "git_stash_create", "sha": stash_sha}
        return {"method": "git_clean", "reason": "no_uncommitted_changes"}

    def restore(self) -> dict[str, Any]:
        if not self._is_git or not self._stash_id:
            return {"restored": False, "reason": "no_rescue_point"}
        result = subprocess.run(
            ["git", "stash", "apply", self._stash_id],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        return {"restored": result.returncode == 0, "sha": self._stash_id}

    def cleanup_ref(self) -> None:
        if self._is_git:
            subprocess.run(
                ["git", "update-ref", "-d", "refs/bomba/rescue"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
