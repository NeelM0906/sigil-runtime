from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
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


class ToolExecutorTests(unittest.TestCase):
    def test_schema_generation_and_alias_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir(parents=True, exist_ok=True)
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-tools")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_fs_tools())

            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-tools"),
                available_tools=executor.known_tool_names(),
            )
            openai_schemas = executor.available_tool_schemas(policy, format="openai")
            anthropic_schemas = executor.available_tool_schemas(policy, format="anthropic")
            self.assertTrue(any(item["function"]["name"] == "read" for item in openai_schemas))
            self.assertTrue(any(item["name"] == "read" for item in anthropic_schemas))

            context = ToolContext(
                tenant_id="tenant-tools",
                session_id="s1",
                turn_id="t1",
                user_id="u1",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            write = executor.execute(
                "write",
                {"path": "a.txt", "content": "hello"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(write.status, "executed")

            read_via_alias = executor.execute(
                "read_file",
                {"path": "a.txt"},
                context=context,
                policy=policy,
                confidence=1.0,
            )
            self.assertEqual(read_via_alias.status, "executed")
            self.assertIn("hello", read_via_alias.output["content"])


if __name__ == "__main__":
    unittest.main()
