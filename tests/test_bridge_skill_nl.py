from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class BridgeSkillNlTests(unittest.TestCase):
    def test_nl_trust_query_bypasses_llm(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / ".runtime"
            workspace = Path(td) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home), provider=StaticEchoProvider())
            bridge.get_skill_source_trust = lambda tenant_id, workspace_root=None: {  # type: ignore[method-assign]
                "clawhub": "allow_with_approval",
                "anthropic_skills": "allow_with_approval",
            }
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="t1",
                    session_id="s1",
                    user_id="u1",
                    user_message="show trust settings",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertEqual(result["turn"]["mode"], "skill_nl")
            self.assertEqual(result["assistant"]["provider"], "skill_nl_router")
            self.assertIn("source_trust", result["assistant"]["text"])

    def test_nl_install_request_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / ".runtime"
            workspace = Path(td) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home), provider=StaticEchoProvider())
            bridge.create_skill_install_request = lambda **kwargs: {  # type: ignore[method-assign]
                "request_id": "req-1",
                "approval_id": "app-1",
                "status": "pending_approval",
                "source": kwargs["source"],
                "skill_id": kwargs["skill_id"],
            }
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id="t1",
                    session_id="s1",
                    user_id="u1",
                    user_message="install skill daily-brief from clawhub",
                    profile=TurnProfile.CHAT,
                    workspace_root=str(workspace),
                )
            )
            self.assertEqual(result["turn"]["mode"], "skill_nl")
            self.assertIn("pending_approval", result["assistant"]["text"])
            self.assertIn("next_step", result["assistant"]["text"])


if __name__ == "__main__":
    unittest.main()
