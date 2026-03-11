from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.search.agentic_search import AgenticSearchExecutor, SearchPlan


class AgenticSearchTests(unittest.TestCase):
    def test_two_pass_balanced_escalates_on_miss(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "main.ts").write_text("export const answer = 42;\n", encoding="utf-8")

            exe = AgenticSearchExecutor(root)
            plan = SearchPlan(
                query="NonExistingIdentifierXYZ",
                intent="symbol_lookup",
                scope=["src"],
                file_types=["ts"],
                escalation_allowed=True,
                escalation_mode="balanced",
            )
            pack = exe.execute(plan)
            self.assertEqual(pack.pass_number, 2)
            self.assertTrue(pack.escalated)
            self.assertEqual(len(pack.results), 0)

    def test_no_escalation_when_high_conf_hits(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "handler.ts").write_text(
                "function paymentHandler() { return 'ok'; }\n",
                encoding="utf-8",
            )

            exe = AgenticSearchExecutor(root)
            plan = SearchPlan(
                query="paymentHandler",
                intent="symbol_lookup",
                scope=["src"],
                file_types=["ts"],
                escalation_allowed=True,
                escalation_mode="balanced",
            )
            pack = exe.execute(plan)
            self.assertEqual(pack.pass_number, 1)
            self.assertFalse(pack.escalated)
            self.assertGreaterEqual(len(pack.results), 1)

    def test_fallback_when_rg_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "agent.py").write_text(
                "def greet():\n    return 'hello'\n",
                encoding="utf-8",
            )

            exe = AgenticSearchExecutor(root)
            exe._rg_available = False  # simulate missing ripgrep
            plan = SearchPlan(
                query="greet",
                intent="symbol_lookup",
                scope=["src"],
                file_types=["py"],
                escalation_allowed=True,
                escalation_mode="balanced",
            )
            pack = exe.execute(plan)
            self.assertGreaterEqual(len(pack.results), 1)
            self.assertIn("python-fallback-search", pack.commands[0])

    def test_fallback_when_query_is_multiline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "agent.md").write_text(
                "alpha line\nbeta line\ngamma line\n",
                encoding="utf-8",
            )

            exe = AgenticSearchExecutor(root)
            plan = SearchPlan(
                query="alpha line\nbeta line",
                intent="targeted_lookup",
                scope=["src"],
                file_types=["md"],
                escalation_allowed=True,
                escalation_mode="balanced",
            )
            pack = exe.execute(plan)
            self.assertGreaterEqual(len(pack.results), 1)
            self.assertIn("python-fallback-search", pack.commands[0])
            self.assertIn("multiline-query", pack.commands[0])


if __name__ == "__main__":
    unittest.main()
