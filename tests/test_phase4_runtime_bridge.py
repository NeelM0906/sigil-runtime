from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class RuntimeBridgeTests(unittest.TestCase):
    def test_handle_turn_records_learning_without_artifact_for_simple_chat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "main.py").write_text("def payment_handler():\n    return 1\n", encoding="utf-8")

            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )

            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-d",
                    session_id=str(uuid.uuid4()),
                    user_id="user-d",
                    user_message="I prefer Neovim for coding",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )

            self.assertIn("assistant", result)
            self.assertTrue(result["assistant"]["text"])
            self.assertEqual(result["artifacts"], [])
            self.assertTrue(result["codeintel"]["serena_enabled"])
            self.assertTrue(result["codeintel"]["serena_edit_tools_enabled"])
            self.assertIn(result["memory"]["learning"]["status"], {"applied", "pending"})

    def test_handle_turn_creates_markdown_artifact_on_explicit_deliverable_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(
                config=RuntimeConfig(runtime_home=runtime_home),
                provider=StaticEchoProvider(),
            )
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="tenant-deliverable",
                    session_id=str(uuid.uuid4()),
                    user_id="user-deliverable",
                    user_message="create a markdown report for today status",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )

            self.assertTrue(result["artifacts"])
            self.assertEqual(result["artifacts"][0]["type"], "markdown")


if __name__ == "__main__":
    unittest.main()
