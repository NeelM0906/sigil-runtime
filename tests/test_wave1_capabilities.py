from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from bomba_sr.models.capabilities import ModelCapabilityService
from bomba_sr.storage.db import RuntimeDB


class ModelCapabilitiesTests(unittest.TestCase):
    def test_fetch_and_cache(self) -> None:
        calls = {"n": 0}

        def fetcher() -> list[dict]:
            calls["n"] += 1
            return [
                {
                    "id": "anthropic/claude-opus-4.6",
                    "context_length": 1_000_000,
                    "supported_parameters": ["tools", "response_format"],
                    "top_provider": {
                        "context_length": 1_000_000,
                        "max_completion_tokens": 128_000,
                    },
                }
            ]

        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            svc = ModelCapabilityService(db=db, fetcher=fetcher, cache_ttl_seconds=60)

            first = svc.get_capabilities("anthropic/claude-opus-4.6")
            self.assertEqual(first.context_length, 1_000_000)
            self.assertEqual(first.max_completion_tokens, 128_000)
            self.assertTrue(first.supports_tools)
            self.assertTrue(first.supports_json_mode)
            self.assertEqual(calls["n"], 1)

            second = svc.get_capabilities("anthropic/claude-opus-4.6")
            self.assertEqual(second.context_length, 1_000_000)
            self.assertEqual(calls["n"], 1, "second call should hit cache")

    def test_cache_expiry_refreshes(self) -> None:
        calls = {"n": 0}

        def fetcher() -> list[dict]:
            calls["n"] += 1
            return [
                {
                    "id": "openai/gpt-5.2-codex",
                    "context_length": 400_000,
                    "supported_parameters": ["tools"],
                    "top_provider": {
                        "context_length": 400_000,
                        "max_completion_tokens": 128_000,
                    },
                }
            ]

        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            svc = ModelCapabilityService(db=db, fetcher=fetcher, cache_ttl_seconds=1)

            now = datetime.now(timezone.utc)
            svc.get_capabilities("openai/gpt-5.2-codex", now=now)
            self.assertEqual(calls["n"], 1)

            later = now + timedelta(seconds=2)
            svc.get_capabilities("openai/gpt-5.2-codex", now=later)
            self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
