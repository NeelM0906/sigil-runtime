from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_prove_ahead import (
    ACT_I_PROFILE,
    MATRIX_DIMENSIONS,
    builtin_prove_ahead_tools,
)


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


def _setup_prove_ahead_data(tmpdir: Path) -> None:
    data_dir = tmpdir / "prove-ahead" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "competitors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE competitors (
            company_name TEXT PRIMARY KEY,
            product TEXT,
            category TEXT,
            pricing_model TEXT,
            pricing_details TEXT,
            capabilities TEXT,
            known_customers TEXT,
            funding TEXT,
            key_differentiators TEXT,
            sources TEXT,
            scores TEXT,
            is_act_i INTEGER DEFAULT 0
        )
    """)
    test_competitor = {
        "company_name": "TestCorp",
        "product": "Test Product",
        "category": "Voice AI",
        "pricing_model": "Usage-based",
        "pricing_details": "$0.10/min",
        "capabilities": json.dumps(["AI calls", "API integration"]),
        "known_customers": "Some customers",
        "funding": "$10M Series A",
        "key_differentiators": "Fast deployment",
        "sources": json.dumps(["https://example.com"]),
        "scores": json.dumps({
            "emotional_intelligence": 3,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 2,
            "voice_quality": 4,
            "customization_depth": 3,
            "integration_breadth": 4,
            "pricing_model": 4,
            "scale": 4,
            "results_tracking": 2,
        }),
        "is_act_i": 0,
    }
    conn.execute(
        "INSERT INTO competitors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(test_competitor.values()),
    )
    conn.commit()
    conn.close()

    # Write a benchmark results file
    benchmark = {
        "generated_at": "2026-02-28T00:00:00+00:00",
        "scenario": {"name": "test"},
        "metadata": {"model": "test-model", "mode_by_agent": {"act_i": "fallback", "generic": "fallback"}},
        "rubric_weights": {"rapport_empathy": 0.2},
        "responses": {"act_i": "test response", "generic": "generic response"},
        "scores": {
            "act_i": {"weighted_total": 8.0},
            "generic": {"weighted_total": 5.0},
        },
        "summary": {"winner": "ACT-I", "weighted_gap": 3.0, "interpretation": "test"},
    }
    (tmpdir / "prove-ahead" / "benchmark_results.json").write_text(json.dumps(benchmark))

    # Write a report
    (tmpdir / "prove-ahead" / "report.md").write_text("# Competitive Analysis\nACT-I leads in all dimensions.")


class _FakeProvider:
    provider_name = "fake"

    def generate(self, model, messages, tools=None):
        class _Resp:
            content = "Hi Jordan, thanks for taking a minute. I respect your budget concerns."
            usage = None
            stop_reason = "end_turn"
        return _Resp()


class ProveAheadToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        _setup_prove_ahead_data(self.tmpdir)
        self.provider = _FakeProvider()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tools_are_created(self) -> None:
        tools = builtin_prove_ahead_tools(
            provider=self.provider,
            workspace_root=self.tmpdir,
        )
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {"prove_ahead_competitors", "prove_ahead_matrix", "prove_ahead_benchmark", "prove_ahead_report"},
        )

    def test_competitors_list(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        comp_tool = next(t for t in tools if t.name == "prove_ahead_competitors")
        result = comp_tool.execute({"include_act_i": True}, _context(self.tmpdir))
        self.assertEqual(result["count"], 2)  # ACT-I + TestCorp
        companies = [c["company"] for c in result["competitors"]]
        self.assertIn("ACT-I", companies)
        self.assertIn("TestCorp", companies)

    def test_competitors_without_act_i(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        comp_tool = next(t for t in tools if t.name == "prove_ahead_competitors")
        result = comp_tool.execute({"include_act_i": False}, _context(self.tmpdir))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["competitors"][0]["company"], "TestCorp")

    def test_matrix(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        matrix_tool = next(t for t in tools if t.name == "prove_ahead_matrix")
        result = matrix_tool.execute({}, _context(self.tmpdir))
        self.assertIn("matrix", result)
        self.assertIn("gaps", result)
        self.assertEqual(len(result["matrix"]), 2)  # ACT-I + TestCorp
        # ACT-I should rank first (higher total score)
        self.assertTrue(result["matrix"][0]["is_act_i"])

    def test_benchmark_cached(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        bench_tool = next(t for t in tools if t.name == "prove_ahead_benchmark")
        result = bench_tool.execute({"use_cached": True}, _context(self.tmpdir))
        self.assertEqual(result["summary"]["winner"], "ACT-I")
        self.assertEqual(result["summary"]["weighted_gap"], 3.0)

    def test_benchmark_fresh(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        bench_tool = next(t for t in tools if t.name == "prove_ahead_benchmark")
        result = bench_tool.execute({"use_cached": False}, _context(self.tmpdir))
        self.assertIn("scores", result)
        self.assertIn("act_i", result["scores"])
        self.assertIn("generic", result["scores"])

    def test_benchmark_fallback_no_provider(self) -> None:
        tools = builtin_prove_ahead_tools(provider=None, workspace_root=self.tmpdir)
        bench_tool = next(t for t in tools if t.name == "prove_ahead_benchmark")
        result = bench_tool.execute({}, _context(self.tmpdir))
        # Should use fallback responses
        self.assertEqual(result["metadata"]["mode_by_agent"]["act_i"], "fallback")
        self.assertEqual(result["metadata"]["mode_by_agent"]["generic"], "fallback")

    def test_report(self) -> None:
        tools = builtin_prove_ahead_tools(provider=self.provider, workspace_root=self.tmpdir)
        report_tool = next(t for t in tools if t.name == "prove_ahead_report")
        result = report_tool.execute({}, _context(self.tmpdir))
        self.assertIn("Competitive Analysis", result["report_markdown"])
        self.assertIsNotNone(result["benchmark_summary"])
        self.assertEqual(result["matrix_summary"]["total_competitors"], 2)


if __name__ == "__main__":
    unittest.main()
