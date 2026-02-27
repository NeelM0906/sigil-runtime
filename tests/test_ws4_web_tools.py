from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import ToolProfile
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_web import builtin_web_tools


class WebToolsTests(unittest.TestCase):
    def _context(self, root: Path, db: RuntimeDB) -> ToolContext:
        return ToolContext(
            tenant_id="tenant-web",
            session_id="session-web",
            turn_id="turn-web",
            user_id="user-web",
            workspace_root=root,
            db=db,
            guard_path=lambda p: (root / p).resolve(),
        )

    def test_web_search_duckduckgo_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = RuntimeDB(root / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-web")
            pipeline = PolicyPipeline(governance=governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_web_tools(brave_api_key=None))
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.RESEARCH, tenant_id="tenant-web"),
                available_tools=executor.known_tool_names(),
            )

            payload = {
                "AbstractURL": "https://example.com/intro",
                "Abstract": "Example summary",
                "Heading": "Example",
                "RelatedTopics": [
                    {"Text": "Topic A", "FirstURL": "https://example.com/a"},
                ],
            }

            def fake_http_get(url, headers=None, timeout=20):  # noqa: ANN001
                return json.dumps(payload).encode("utf-8"), "application/json"

            with patch("bomba_sr.tools.builtin_web._http_get", side_effect=fake_http_get):
                out = executor.execute(
                    tool_name="web_search",
                    arguments={"query": "example", "limit": 2},
                    context=self._context(root, db),
                    policy=policy,
                    confidence=1.0,
                )
            self.assertEqual(out.status, "executed")
            self.assertEqual(out.output.get("provider"), "duckduckgo")
            self.assertTrue(out.output.get("results"))

    def test_web_fetch_html_to_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = RuntimeDB(root / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-web")
            pipeline = PolicyPipeline(governance=governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register_many(builtin_web_tools(brave_api_key=None))
            policy = pipeline.resolve(
                ToolPolicyContext(profile=ToolProfile.RESEARCH, tenant_id="tenant-web"),
                available_tools=executor.known_tool_names(),
            )

            html_doc = "<html><body><h1>Title</h1><p>Hello world.</p></body></html>"

            def fake_http_get(url, headers=None, timeout=20):  # noqa: ANN001
                return html_doc.encode("utf-8"), "text/html"

            with patch("bomba_sr.tools.builtin_web._http_get", side_effect=fake_http_get):
                out = executor.execute(
                    tool_name="web_fetch",
                    arguments={"url": "https://example.com", "max_chars": 5000},
                    context=self._context(root, db),
                    policy=policy,
                    confidence=1.0,
                )
            self.assertEqual(out.status, "executed")
            self.assertIn("Title", out.output.get("content", ""))
            self.assertIn("Hello world", out.output.get("content", ""))


if __name__ == "__main__":
    unittest.main()
