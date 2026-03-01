from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_colosseum import builtin_colosseum_tools


def _context(workspace: Path) -> ToolContext:
    return ToolContext(
        tenant_id="tenant",
        session_id="session",
        turn_id="turn",
        user_id="user",
        workspace_root=workspace,
        db=RuntimeDB(":memory:"),
        guard_path=lambda p: Path(p),
    )


def _setup_colosseum_data(tmpdir: Path) -> None:
    data_dir = tmpdir / "colosseum" / "v2" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "results").mkdir(exist_ok=True)

    beings = [
        {
            "id": "test_area_leader",
            "title": "Test Leader",
            "area": "Test Area",
            "area_key": "test_area",
            "type": "leader",
            "focus": "Test focus",
            "dna": "You are a test being.",
            "generation": 0,
        },
        {
            "id": "test_area_zone_action",
            "title": "Test Zone Action",
            "area": "Test Area",
            "area_key": "test_area",
            "type": "zone_action",
            "focus": "Zone action focus",
            "dna": "You are a zone action test being.",
            "generation": 0,
        },
    ]
    scenarios = {
        "test_area_leader": {
            "title": "Test Scenario Leader",
            "company": "ACT-I",
            "situation": "A test situation.",
            "person": {"name": "Test Person", "role": "Tester"},
            "success_criteria": "Test passes",
        },
        "test_area_zone_action": {
            "title": "Test Scenario Zone",
            "company": "Unblinded",
            "situation": "Another test situation.",
            "person": {"name": "Zone Person", "role": "Tester"},
            "success_criteria": "Zone test passes",
        },
    }
    judges = {
        "test_judge": {
            "name": "Test Judge",
            "focus": "Testing",
            "prompt": "You are a test judge. Return JSON: {\"overall\": 7.5, \"feedback\": \"test\"}",
        }
    }

    (data_dir / "beings.json").write_text(json.dumps(beings))
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))
    (data_dir / "judges.json").write_text(json.dumps(judges))


class _FakeProvider:
    provider_name = "fake"
    _call_count = 0

    def generate(self, model, messages, tools=None):
        self._call_count += 1

        class _Resp:
            content = '{"overall": 7.5, "feedback": "test feedback"}'
            usage = None
            stop_reason = "end_turn"
        # If it's a being response (system message is DNA-like)
        for m in messages:
            if m.role == "system" and "being" in m.content.lower():
                _Resp.content = "Test being response with some masterful content."
                break
        return _Resp()


class ColosseumToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        _setup_colosseum_data(self.tmpdir)
        self.provider = _FakeProvider()

    def test_tools_are_created(self) -> None:
        tools = builtin_colosseum_tools(
            provider=self.provider,
            default_model_id="test-model",
            workspace_root=self.tmpdir,
        )
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {"colosseum_run_round", "colosseum_leaderboard", "colosseum_being_list", "colosseum_evolve", "colosseum_scenario_list"},
        )

    def test_being_list(self) -> None:
        tools = builtin_colosseum_tools(provider=self.provider, workspace_root=self.tmpdir)
        being_list = next(t for t in tools if t.name == "colosseum_being_list")
        result = being_list.execute({}, _context(self.tmpdir))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["beings"][0]["id"], "test_area_leader")

    def test_being_list_with_area_filter(self) -> None:
        tools = builtin_colosseum_tools(provider=self.provider, workspace_root=self.tmpdir)
        being_list = next(t for t in tools if t.name == "colosseum_being_list")
        result = being_list.execute({"area_filter": "test_area"}, _context(self.tmpdir))
        self.assertEqual(result["count"], 2)
        result_other = being_list.execute({"area_filter": "nonexistent"}, _context(self.tmpdir))
        self.assertEqual(result_other["count"], 0)

    def test_scenario_list(self) -> None:
        tools = builtin_colosseum_tools(provider=self.provider, workspace_root=self.tmpdir)
        scenario_list = next(t for t in tools if t.name == "colosseum_scenario_list")
        result = scenario_list.execute({}, _context(self.tmpdir))
        self.assertEqual(result["count"], 2)

    def test_leaderboard_empty(self) -> None:
        tools = builtin_colosseum_tools(provider=self.provider, workspace_root=self.tmpdir)
        lb = next(t for t in tools if t.name == "colosseum_leaderboard")
        result = lb.execute({}, _context(self.tmpdir))
        self.assertEqual(result["leaderboard"], [])
        self.assertIn("No tournament results", result.get("message", ""))

    def test_run_round_and_leaderboard(self) -> None:
        tools = builtin_colosseum_tools(
            provider=self.provider,
            default_model_id="test-model",
            workspace_root=self.tmpdir,
        )
        run_tool = next(t for t in tools if t.name == "colosseum_run_round")
        result = run_tool.execute({"max_beings": 2}, _context(self.tmpdir))
        self.assertEqual(result["round_results"], 2)
        self.assertIn("top_5", result)

        # Leaderboard should now have data
        lb = next(t for t in tools if t.name == "colosseum_leaderboard")
        lb_result = lb.execute({}, _context(self.tmpdir))
        self.assertGreater(len(lb_result["leaderboard"]), 0)

    def test_evolve_requires_leaderboard(self) -> None:
        tools = builtin_colosseum_tools(provider=self.provider, workspace_root=self.tmpdir)
        evolve = next(t for t in tools if t.name == "colosseum_evolve")
        result = evolve.execute({}, _context(self.tmpdir))
        self.assertIn("error", result)

    def test_run_round_with_being_id_filter(self) -> None:
        tools = builtin_colosseum_tools(
            provider=self.provider,
            default_model_id="test-model",
            workspace_root=self.tmpdir,
        )
        run_tool = next(t for t in tools if t.name == "colosseum_run_round")
        result = run_tool.execute({"being_ids": ["test_area_leader"]}, _context(self.tmpdir))
        self.assertEqual(result["round_results"], 1)


if __name__ == "__main__":
    unittest.main()
