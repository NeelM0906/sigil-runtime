from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bomba_sr.governance.policy_pipeline import PolicyPipeline
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.llm.providers import LLMResponse
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolExecutor


class _DummyProvider:
    provider_name = "openai"

    def generate(self, model, messages, tools=None):  # pragma: no cover - not used in these tests
        raise AssertionError("not expected")


class LoopResponseParsingTests(unittest.TestCase):
    def _loop(self) -> AgenticLoop:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        db = RuntimeDB(Path(td.name) / "runtime.db")
        governance = ToolGovernanceService(db)
        pipeline = PolicyPipeline(governance)
        executor = ToolExecutor(governance, pipeline)
        return AgenticLoop(provider=_DummyProvider(), tool_executor=executor, config=LoopConfig())

    def test_parse_openai_tool_calls(self) -> None:
        loop = self._loop()
        response = LLMResponse(
            text="",
            model="m",
            usage=None,
            raw={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {"name": "read", "arguments": json.dumps({"path": "a.txt"})},
                                }
                            ],
                        }
                    }
                ]
            },
            stop_reason="tool_calls",
        )
        calls = loop._parse_tool_calls(response)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].id, "c1")
        self.assertEqual(calls[0].name, "read")
        self.assertEqual(calls[0].arguments["path"], "a.txt")

    def test_parse_anthropic_tool_use_blocks(self) -> None:
        loop = self._loop()
        response = LLMResponse(
            text="",
            model="m",
            usage=None,
            raw={
                "content": [
                    {"type": "text", "text": "thinking"},
                    {"type": "tool_use", "id": "t1", "name": "grep", "input": {"pattern": "TODO"}},
                ]
            },
            stop_reason="tool_use",
        )
        calls = loop._parse_tool_calls(response)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].id, "t1")
        self.assertEqual(calls[0].name, "grep")
        self.assertEqual(calls[0].arguments["pattern"], "TODO")


if __name__ == "__main__":
    unittest.main()
