from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_fs import builtin_fs_tools


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_real = root.resolve()
        if candidate != root_real and root_real not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class FSToolsTests(unittest.TestCase):
    def test_read_write_edit_and_path_guard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-fs")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_fs_tools())

            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-fs"),
                available_tools=executor.known_tool_names(),
            )
            context = ToolContext(
                tenant_id="tenant-fs",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )

            write = executor.execute(
                "write",
                {"path": "notes/todo.txt", "content": "alpha beta"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(write.status, "executed")

            read = executor.execute(
                "read",
                {"path": "notes/todo.txt"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(read.status, "executed")
            self.assertEqual(read.output["content"], "alpha beta")

            edit = executor.execute(
                "edit",
                {"path": "notes/todo.txt", "old_string": "alpha", "new_string": "ALPHA"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(edit.status, "executed")

            escaped = executor.execute(
                "read",
                {"path": "../outside.txt"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(escaped.status, "error")
            self.assertIn("path escapes workspace", escaped.output["error"])


if __name__ == "__main__":
    unittest.main()
