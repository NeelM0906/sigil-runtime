from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from bomba_sr.adaptation.runtime_adaptation import RuntimeAdaptationEngine
from bomba_sr.storage.db import RuntimeDB


class RuntimeAdaptationTests(unittest.TestCase):
    def test_aggregate_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            engine = RuntimeAdaptationEngine(db)

            now = datetime.now(timezone.utc)
            p0 = (now - timedelta(hours=2)).isoformat()
            p1 = (now - timedelta(hours=1)).isoformat()

            engine.ingest_search_metric(escalated=False, precision_at_k=0.8, execution_ms=100, created_at=p0)
            engine.ingest_search_metric(escalated=True, precision_at_k=0.6, execution_ms=140, created_at=p0)
            engine.ingest_subagent_metric(status="completed", runtime_ms=900, created_at=p0)
            engine.ingest_subagent_metric(status="failed", runtime_ms=700, created_at=p0)
            engine.ingest_prediction_metric(brier_score=0.18, ece=0.07, created_at=p0)
            engine.ingest_loop_incident(created_at=p0)

            rollup = engine.aggregate_period(period_start=p0, period_end=p1)
            self.assertAlmostEqual(rollup.retrieval_precision_at_k, 0.7, places=5)
            self.assertAlmostEqual(rollup.search_escalation_rate, 0.5, places=5)
            self.assertAlmostEqual(rollup.subagent_success_rate, 0.5, places=5)
            self.assertGreaterEqual(rollup.subagent_p95_latency_ms, 700)
            self.assertEqual(rollup.loop_detector_incidents, 1)

    def test_policy_versioning_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            engine = RuntimeAdaptationEngine(db)

            v1 = engine.update_policy("context_policy", {"compression": {"mode": "balanced"}}, reason="initial")
            self.assertEqual(v1["version"], 1)

            v2 = engine.update_policy("context_policy", {"compression": {"mode": "strict"}}, reason="tighten")
            self.assertEqual(v2["version"], 2)

            rb = engine.rollback_policy("context_policy", target_version=1, reason="regression")
            self.assertEqual(rb["version"], 3)
            self.assertEqual(rb["rolled_back_from"], 2)

            current = engine.get_policy("context_policy")
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current["version"], 3)
            self.assertEqual(current["policy"]["compression"]["mode"], "balanced")

    def test_regression_detection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(f"{td}/runtime.db")
            engine = RuntimeAdaptationEngine(db)

            now = datetime.now(timezone.utc)
            a0 = (now - timedelta(hours=4)).isoformat()
            a1 = (now - timedelta(hours=3)).isoformat()
            b0 = (now - timedelta(hours=2)).isoformat()
            b1 = (now - timedelta(hours=1)).isoformat()

            # Good period
            engine.ingest_search_metric(escalated=False, precision_at_k=0.9, execution_ms=90, created_at=a0)
            engine.ingest_subagent_metric(status="completed", runtime_ms=500, created_at=a0)
            engine.aggregate_period(period_start=a0, period_end=a1)

            # Regressed period
            engine.ingest_search_metric(escalated=True, precision_at_k=0.2, execution_ms=180, created_at=b0)
            engine.ingest_subagent_metric(status="failed", runtime_ms=1500, created_at=b0)
            engine.ingest_loop_incident(created_at=b0)
            engine.aggregate_period(period_start=b0, period_end=b1)

            verdict = engine.detect_regression("context_policy")
            self.assertTrue(verdict["regression"])
            self.assertIn("retrieval_precision_declined", verdict["reasons"])
            self.assertIn("search_escalation_increased", verdict["reasons"])


if __name__ == "__main__":
    unittest.main()
