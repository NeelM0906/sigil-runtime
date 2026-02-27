from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.storage.db import RuntimeDB


class PolicyPipelineTests(unittest.TestCase):
    def test_global_allow_deny_layers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-p")
            pipeline = PolicyPipeline(
                governance=governance,
                global_allow=("read", "write", "exec"),
                global_deny=("exec",),
            )
            resolved = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-p"),
                available_tools=("read", "write", "exec", "grep"),
            )
            self.assertEqual(resolved.allowed_tools, frozenset({"read", "write"}))
            self.assertEqual(resolved.denied_tools, frozenset({"exec"}))
            self.assertTrue(pipeline.is_tool_allowed("read", resolved))
            self.assertFalse(pipeline.is_tool_allowed("exec", resolved))

    def test_tenant_allow_deny_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(Path(td) / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-q")
            db.execute(
                """
                INSERT INTO tool_governance_policies (id, tenant_id, policy_name, version, policy_json, created_at)
                VALUES (?, ?, 'default', ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "tenant-q",
                    999,
                    json.dumps(
                        {
                            "thresholds": {"low": 0.2, "medium": 0.4, "high": 0.75, "critical": 0.99},
                            "allow": ["read", "write", "grep"],
                            "deny": ["write"],
                        },
                        separators=(",", ":"),
                    ),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            db.commit()

            pipeline = PolicyPipeline(governance=governance)
            resolved = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.FULL, tenant_id="tenant-q"),
                available_tools=("read", "write", "grep", "exec"),
            )
            self.assertEqual(resolved.allowed_tools, frozenset({"read", "grep"}))
            self.assertIn("write", resolved.denied_tools)


if __name__ == "__main__":
    unittest.main()
