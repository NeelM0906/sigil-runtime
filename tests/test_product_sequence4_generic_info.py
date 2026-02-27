from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class ProductSequence4GenericInfoTests(unittest.TestCase):
    def test_generic_info_mode_uses_retriever(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)

            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home), provider=StaticEchoProvider())
            tenant = "tenant-info"

            runtime = bridge._tenant_runtime(tenant, str(workspace))
            runtime.info.retrieve = lambda q, limit=2: [  # type: ignore[assignment]
                type("S", (), {"title": "Python", "source_url": "https://example.com/python", "snippet": "Python is a language.", "confidence": 0.81})()
            ]

            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant,
                    session_id=str(uuid.uuid4()),
                    user_id="user-info",
                    user_message="What is Python?",
                    workspace_root=str(workspace),
                    profile=TurnProfile.CHAT,
                )
            )

            self.assertEqual(result["turn"]["mode"], "generic_info")
            self.assertEqual(result["search"]["pass"], 0)
            self.assertTrue(result["search"]["results"])
            self.assertIn("https://example.com/python", result["search"]["results"][0]["path"])


if __name__ == "__main__":
    unittest.main()
