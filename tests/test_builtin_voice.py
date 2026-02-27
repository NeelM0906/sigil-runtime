from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_voice import builtin_voice_tools


def _ctx() -> ToolContext:
    return ToolContext(
        tenant_id="tenant",
        session_id="session",
        turn_id="turn",
        user_id="user",
        workspace_root=Path.cwd(),
        db=RuntimeDB(":memory:"),
        guard_path=lambda p: Path(p),
    )


class VoiceToolTests(unittest.TestCase):
    def test_provider_gating(self) -> None:
        self.assertEqual(builtin_voice_tools(provider="other"), [])

    def test_list_calls_and_transcript(self) -> None:
        def fake_http(method, url, api_key, payload=None, timeout=30):  # noqa: ANN001
            if url.endswith("/calls?limit=20"):
                return {
                    "calls": [
                        {
                            "call_id": "c1",
                            "from_number": "+100",
                            "to_number": "+200",
                            "duration": 25,
                            "pathway_name": "Onboarding",
                            "created_at": "2026-02-27T00:00:00Z",
                            "status": "completed",
                        }
                    ]
                }
            if url.endswith("/calls/c1"):
                return {
                    "call_id": "c1",
                    "duration": 25,
                    "transcript": [{"role": "assistant", "text": "hi"}],
                    "status": "completed",
                    "account_id": "acct-secret",
                    "webhook_url": "https://example.invalid/hook",
                }
            raise AssertionError(f"unexpected url {url}")

        with (
            patch.dict("os.environ", {"BLAND_API_KEY": "bk"}, clear=False),
            patch("bomba_sr.tools.builtin_voice._http_json", side_effect=fake_http),
        ):
            tools = builtin_voice_tools(provider="bland")
            list_tool = next(t for t in tools if t.name == "voice_list_calls")
            tr_tool = next(t for t in tools if t.name == "voice_get_transcript")
            listed = list_tool.execute({}, _ctx())
            self.assertEqual(len(listed["calls"]), 1)
            self.assertEqual(listed["calls"][0]["call_id"], "c1")
            tr = tr_tool.execute({"call_id": "c1"}, _ctx())
            self.assertEqual(tr["call_id"], "c1")
            self.assertEqual(len(tr["transcript"]), 1)
            self.assertEqual(tr["metadata"].get("status"), "completed")
            self.assertNotIn("account_id", tr["metadata"])
            self.assertNotIn("webhook_url", tr["metadata"])

    def test_make_call_and_risk(self) -> None:
        def fake_http(method, url, api_key, payload=None, timeout=30):  # noqa: ANN001
            if url.endswith("/calls") and method == "POST":
                return {"call_id": "out-1", "status": "queued"}
            if url.endswith("/pathways"):
                return {"pathways": [{"pathway_id": "p1", "name": "test", "description": "d"}]}
            raise AssertionError(f"unexpected url {url}")

        with (
            patch.dict("os.environ", {"BLAND_API_KEY": "bk"}, clear=False),
            patch("bomba_sr.tools.builtin_voice._http_json", side_effect=fake_http),
        ):
            tools = builtin_voice_tools(provider="bland")
            call_tool = next(t for t in tools if t.name == "voice_make_call")
            self.assertEqual(call_tool.risk_level, "high")
            call_result = call_tool.execute({"to_number": "+12015550000", "pathway_id": "p1"}, _ctx())
            self.assertEqual(call_result["call_id"], "out-1")
            path_tool = next(t for t in tools if t.name == "voice_list_pathways")
            pathways = path_tool.execute({}, _ctx())
            self.assertEqual(pathways["pathways"][0]["pathway_id"], "p1")

    def test_missing_api_key_raises(self) -> None:
        with patch.dict("os.environ", {"BLAND_API_KEY": ""}, clear=False):
            tools = builtin_voice_tools(provider="bland")
            list_tool = next(t for t in tools if t.name == "voice_list_calls")
            with self.assertRaises(ValueError):
                list_tool.execute({}, _ctx())

    def test_rejects_unsafe_identifier_args(self) -> None:
        with patch.dict("os.environ", {"BLAND_API_KEY": "bk"}, clear=False):
            tools = builtin_voice_tools(provider="bland")
            tr_tool = next(t for t in tools if t.name == "voice_get_transcript")
            call_tool = next(t for t in tools if t.name == "voice_make_call")
            with self.assertRaises(ValueError):
                tr_tool.execute({"call_id": "../admin/keys"}, _ctx())
            with self.assertRaises(ValueError):
                call_tool.execute(
                    {"to_number": "+12015550000", "pathway_id": "../pathway"},
                    _ctx(),
                )
            with self.assertRaises(ValueError):
                call_tool.execute(
                    {"to_number": "2015550000", "pathway_id": "path-1"},
                    _ctx(),
                )


if __name__ == "__main__":
    unittest.main()
