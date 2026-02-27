from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.llm.providers import StaticEchoProvider
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.runtime.config import RuntimeConfig


class ProductSequence5IdentityTests(unittest.TestCase):
    def test_identity_profile_and_pending_signals(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime_home = Path(td) / "runtime-home"
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "x.py").write_text("print('x')\n", encoding="utf-8")

            bridge = RuntimeBridge(config=RuntimeConfig(runtime_home=runtime_home), provider=StaticEchoProvider())
            tenant = "tenant-id"
            user = "user-id"

            bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant,
                    session_id=str(uuid.uuid4()),
                    user_id=user,
                    user_message="my name is Neel and I prefer neovim",
                    workspace_root=str(workspace),
                    profile=TurnProfile.CHAT,
                )
            )
            bridge.handle_turn(
                TurnRequest(
                    tenant_id=tenant,
                    session_id=str(uuid.uuid4()),
                    user_id=user,
                    user_message="don't touch payment code",
                    workspace_root=str(workspace),
                    profile=TurnProfile.CHAT,
                )
            )

            profile = bridge.get_user_profile(tenant, user, workspace_root=str(workspace))
            self.assertEqual(profile["display_name"], "Neel")
            self.assertTrue(profile["preferences"])

            pending = bridge.list_pending_profile_signals(tenant, user, workspace_root=str(workspace))
            self.assertTrue(pending)
            self.assertEqual(pending[0]["status"], "pending")

            decided = bridge.decide_profile_signal(
                tenant_id=tenant,
                user_id=user,
                signal_id=pending[0]["signal_id"],
                approved=True,
                workspace_root=str(workspace),
            )
            self.assertEqual(decided["status"], "applied")


if __name__ == "__main__":
    unittest.main()
