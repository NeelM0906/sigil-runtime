"""Tests for the Dream Cycle memory consolidation engine.

Verifies:
  - Phase 1 (Gather): collects memories from all sources
  - Phase 2 (Consolidate): removes duplicates, resolves contradictions, archives stale
  - Phase 3 (Derive): generates new insights from accumulated data
  - Phase 4 (Prune): archives excess memories beyond threshold
  - Phase 5 (Cross-pollinate): shares insights between beings
  - Lifecycle: start/stop/status
  - Failure tolerance: LLM errors don't crash the cycle
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.memory.dreaming import (
    DreamCycle,
    MEMORY_PRUNE_THRESHOLD,
    DERIVED_INSIGHT_CONFIDENCE,
    CROSS_POLLINATE_CONFIDENCE,
)
from bomba_sr.storage.db import RuntimeDB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dream_cycle(with_memories: int = 0, being_ids: list[str] | None = None):
    """Build a DreamCycle with mocked bridge, dashboard, and optional seeded memories."""
    tmpdir = tempfile.mkdtemp()
    db = RuntimeDB(os.path.join(tmpdir, "runtime.db"))

    # Create memory tables (including being_id columns)
    db.script("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            memory_key TEXT NOT NULL,
            tier TEXT NOT NULL,
            content TEXT NOT NULL,
            entities TEXT NOT NULL,
            evidence_refs TEXT NOT NULL,
            recency_ts TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            being_id TEXT,
            UNIQUE(user_id, memory_key, version)
        );
        CREATE TABLE IF NOT EXISTS memory_archive (
            id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            memory_key TEXT NOT NULL,
            old_content TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS procedural_memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            strategy_key TEXT NOT NULL,
            content TEXT NOT NULL,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            being_id TEXT,
            UNIQUE(user_id, strategy_key)
        );
        CREATE TABLE IF NOT EXISTS markdown_notes (
            note_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            relative_path TEXT NOT NULL,
            title TEXT NOT NULL,
            tags TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL,
            being_id TEXT
        );
        CREATE TABLE IF NOT EXISTS task_results (
            task_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            goal TEXT NOT NULL,
            strategy TEXT NOT NULL,
            beings_used TEXT NOT NULL,
            outputs TEXT NOT NULL,
            synthesis TEXT NOT NULL,
            artifacts TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
    """)
    db.commit()

    # Seed memories if requested
    import uuid
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    for i in range(with_memories):
        ts = (now - timedelta(days=with_memories - i)).isoformat()
        db.execute(
            """INSERT INTO memories (id, user_id, memory_key, tier, content, entities,
               evidence_refs, recency_ts, active, version, created_at, updated_at)
            VALUES (?, ?, ?, 'semantic', ?, '[]', '[]', ?, 1, 1, ?, ?)""",
            (str(uuid.uuid4()), "forge", f"mem_{i}", f"Memory content #{i}", ts, ts, ts),
        )
    db.commit()

    # Minimal tenant runtime mock
    tenant_runtime = MagicMock()
    tenant_runtime.db = db
    tenant_runtime.memory = MagicMock()
    tenant_runtime.memory._read_note_body = MagicMock(return_value="Note body text")

    bridge = MagicMock()
    bridge._tenant_runtime.return_value = tenant_runtime

    dashboard = MagicMock()
    bids = being_ids or ["forge", "scholar"]
    dashboard.list_beings.return_value = [
        {"id": bid, "name": f"SAI {bid.title()}", "status": "online",
         "tenant_id": f"tenant-{bid}", "workspace": f"workspaces/{bid}"}
        for bid in bids
    ]
    dashboard.get_being.side_effect = lambda bid: {
        "id": bid, "name": f"SAI {bid.title()}", "status": "online",
        "tenant_id": f"tenant-{bid}", "workspace": f"workspaces/{bid}",
    }

    dc = DreamCycle(bridge=bridge, dashboard_svc=dashboard, interval_seconds=60)
    return dc, db, bridge, dashboard, tmpdir


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

class TestDreamCycleLifecycle:
    def test_status_before_start(self):
        dc, *_ = _make_dream_cycle()
        status = dc.status()
        assert status["running"] is False
        assert status["total_runs"] == 0
        assert status["last_run_at"] is None

    def test_start_and_stop(self):
        dc, *_ = _make_dream_cycle()
        dc.start()
        assert dc.is_running() is True
        dc.stop()
        assert dc.is_running() is False

    def test_double_start_is_idempotent(self):
        dc, *_ = _make_dream_cycle()
        dc.start()
        dc.start()  # should not raise
        assert dc.is_running() is True
        dc.stop()


# ---------------------------------------------------------------------------
# Phase 1: Gather
# ---------------------------------------------------------------------------

class TestPhaseGather:
    def test_gather_collects_semantic_memories(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=5)
        being = {"id": "forge", "name": "SAI Forge", "tenant_id": "tenant-forge", "workspace": "workspaces/forge"}
        gathered = dc._phase_gather("forge", being, "tenant-forge")
        assert gathered["has_data"] is True
        assert len(gathered["semantic_memories"]) == 5

    def test_gather_returns_no_data_when_empty(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=0)
        being = {"id": "forge", "name": "SAI Forge", "tenant_id": "tenant-forge", "workspace": "workspaces/forge"}
        gathered = dc._phase_gather("forge", being, "tenant-forge")
        assert gathered["has_data"] is False

    def test_gather_handles_missing_tenant(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle()
        bridge._tenant_runtime.side_effect = RuntimeError("No such tenant")
        being = {"id": "forge", "name": "SAI Forge", "tenant_id": "tenant-forge", "workspace": "workspaces/forge"}
        gathered = dc._phase_gather("forge", being, "tenant-forge")
        assert gathered["has_data"] is False


# ---------------------------------------------------------------------------
# Phase 2: Consolidate
# ---------------------------------------------------------------------------

class TestPhaseConsolidate:
    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_consolidate_removes_duplicates(self, mock_prov):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=5)

        mock_provider = MagicMock()
        mock_provider.generate.return_value = MagicMock(text=json.dumps({
            "duplicates": [{"keep": "mem_0", "remove": ["mem_1"]}],
            "contradictions": [],
            "stale": [],
        }))
        mock_prov.return_value = mock_provider

        gathered = {"semantic_memories": [
            {"key": "mem_0", "content": "Content A"},
            {"key": "mem_1", "content": "Content A (dup)"},
        ], "working_notes": [], "procedural_memories": []}

        result = dc._phase_consolidate("forge", "SAI Forge", gathered)
        assert result["duplicates"] == 1
        assert result["contradictions"] == 0
        assert result["stale"] == 0

    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_consolidate_handles_llm_failure(self, mock_prov):
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = RuntimeError("LLM down")
        mock_prov.return_value = mock_provider

        dc, *_ = _make_dream_cycle()
        gathered = {"semantic_memories": [
            {"key": "mem_0", "content": "Content"},
        ], "working_notes": [], "procedural_memories": []}

        result = dc._phase_consolidate("forge", "SAI Forge", gathered)
        assert "error" in result

    def test_consolidate_skips_when_no_data(self):
        dc, *_ = _make_dream_cycle()
        gathered = {"semantic_memories": [], "working_notes": [], "procedural_memories": []}
        result = dc._phase_consolidate("forge", "SAI Forge", gathered)
        assert result["duplicates"] == 0


# ---------------------------------------------------------------------------
# Phase 3: Derive
# ---------------------------------------------------------------------------

class TestPhaseDerive:
    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_derive_stores_insights(self, mock_prov):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=3)

        mock_provider = MagicMock()
        mock_provider.generate.return_value = MagicMock(text=json.dumps([
            {"key": "derived::pattern_1", "content": "Forge excels at research tasks", "relevance_to_others": ["scholar"]},
            {"key": "derived::pattern_2", "content": "Performance improves with structured prompts", "relevance_to_others": []},
        ]))
        mock_prov.return_value = mock_provider

        gathered = {"semantic_memories": [
            {"key": "mem_0", "content": "Research findings"},
        ], "procedural_memories": [], "task_results": []}

        runtime = bridge._tenant_runtime.return_value
        insights = dc._phase_derive("forge", "SAI Forge", gathered)
        assert len(insights) == 2
        # Verify learn_semantic was called for each insight
        assert runtime.memory.learn_semantic.call_count == 2

        # Check confidence is DERIVED_INSIGHT_CONFIDENCE
        call_kwargs = runtime.memory.learn_semantic.call_args_list[0].kwargs
        assert call_kwargs["confidence"] == DERIVED_INSIGHT_CONFIDENCE

    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_derive_handles_llm_failure(self, mock_prov):
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = RuntimeError("LLM down")
        mock_prov.return_value = mock_provider

        dc, *_ = _make_dream_cycle()
        gathered = {"semantic_memories": [{"key": "x", "content": "y"}], "procedural_memories": [], "task_results": []}
        insights = dc._phase_derive("forge", "SAI Forge", gathered)
        assert insights == []

    def test_derive_skips_when_no_data(self):
        dc, *_ = _make_dream_cycle()
        gathered = {"semantic_memories": [], "procedural_memories": [], "task_results": []}
        insights = dc._phase_derive("forge", "SAI Forge", gathered)
        assert insights == []


# ---------------------------------------------------------------------------
# Phase 4: Prune
# ---------------------------------------------------------------------------

class TestPhasePrune:
    def test_prune_archives_excess_memories(self):
        excess = 10
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=MEMORY_PRUNE_THRESHOLD + excess)

        pruned = dc._phase_prune("forge", "tenant-forge")
        assert pruned == excess

        # Verify remaining active count equals threshold
        row = db.execute(
            "SELECT COUNT(*) AS c FROM memories WHERE user_id = 'forge' AND active = 1"
        ).fetchone()
        assert int(row["c"]) == MEMORY_PRUNE_THRESHOLD

        # Verify archived entries exist
        archived = db.execute(
            "SELECT COUNT(*) AS c FROM memory_archive WHERE user_id = 'forge' AND reason = 'dream_prune'"
        ).fetchone()
        assert int(archived["c"]) == excess

    def test_prune_does_nothing_below_threshold(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=10)
        pruned = dc._phase_prune("forge", "tenant-forge")
        assert pruned == 0

    def test_prune_handles_missing_tenant(self):
        dc, *_ = _make_dream_cycle()
        dc.bridge._tenant_runtime.side_effect = RuntimeError("No tenant")
        pruned = dc._phase_prune("forge", "tenant-forge")
        assert pruned == 0


# ---------------------------------------------------------------------------
# Phase 5: Cross-pollinate
# ---------------------------------------------------------------------------

class TestPhaseCrossPollinate:
    def test_cross_pollinate_writes_to_target_being(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(being_ids=["forge", "scholar"])
        runtime = bridge._tenant_runtime.return_value

        insights = [
            {"key": "derived::x", "content": "Forge discovered a pattern", "relevance_to_others": ["scholar"]},
        ]

        count = dc._phase_cross_pollinate("forge", insights)
        assert count == 1
        # Verify learn_semantic was called for scholar
        assert runtime.memory.learn_semantic.call_count == 1
        call_kwargs = runtime.memory.learn_semantic.call_args.kwargs
        assert call_kwargs["confidence"] == CROSS_POLLINATE_CONFIDENCE
        assert "From SAI Forge" in call_kwargs["content"]
        assert call_kwargs["user_id"] == "prime->scholar"

    def test_cross_pollinate_skips_self_and_prime(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(being_ids=["forge", "prime"])
        runtime = bridge._tenant_runtime.return_value

        insights = [
            {"key": "derived::x", "content": "Test", "relevance_to_others": ["forge", "prime"]},
        ]
        count = dc._phase_cross_pollinate("forge", insights)
        assert count == 0  # skips self (forge) and prime

    def test_cross_pollinate_skips_when_no_insights(self):
        dc, *_ = _make_dream_cycle()
        count = dc._phase_cross_pollinate("forge", [])
        assert count == 0

    def test_cross_pollinate_tolerates_failed_write(self):
        dc, db, bridge, dashboard, _ = _make_dream_cycle(being_ids=["forge", "scholar"])
        runtime = bridge._tenant_runtime.return_value
        runtime.memory.learn_semantic.side_effect = RuntimeError("DB error")

        insights = [
            {"key": "derived::x", "content": "Test", "relevance_to_others": ["scholar"]},
        ]
        count = dc._phase_cross_pollinate("forge", insights)
        assert count == 0  # failed, but no exception raised


# ---------------------------------------------------------------------------
# Full cycle integration
# ---------------------------------------------------------------------------

class TestFullDreamCycle:
    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_full_cycle_runs_all_phases(self, mock_prov):
        mock_provider = MagicMock()
        # Consolidate response
        consolidate_resp = MagicMock(text=json.dumps({
            "duplicates": [], "contradictions": [], "stale": [],
        }))
        # Derive response
        derive_resp = MagicMock(text=json.dumps([
            {"key": "derived::test", "content": "Test insight", "relevance_to_others": []},
        ]))
        mock_provider.generate.side_effect = [consolidate_resp, derive_resp]
        mock_prov.return_value = mock_provider

        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=3, being_ids=["forge"])

        results = dc.run_cycle()
        assert "forge" in results
        r = results["forge"]
        assert "being_id" in r
        assert r["being_id"] == "forge"
        assert r["gathered_counts"]["semantic_memories"] == 3
        assert r["derived_count"] == 1

        # Verify cycle counter
        assert dc.status()["total_runs"] == 1
        assert dc.status()["last_run_at"] is not None

    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_full_cycle_skips_unknown_being(self, mock_prov):
        dc, *_ = _make_dream_cycle(being_ids=["forge"])
        dc.dashboard.get_being.side_effect = lambda bid: None if bid == "unknown" else {
            "id": bid, "name": f"SAI {bid.title()}", "tenant_id": f"tenant-{bid}", "workspace": f"workspaces/{bid}",
        }
        results = dc.run_cycle(being_id="unknown")
        assert results["unknown"]["skipped"] is True

    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_cycle_failure_does_not_crash(self, mock_prov):
        """If one being's dream fails, others still run."""
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = RuntimeError("LLM down")
        mock_prov.return_value = mock_provider

        dc, db, bridge, dashboard, _ = _make_dream_cycle(with_memories=3, being_ids=["forge", "scholar"])
        results = dc.run_cycle()
        # Both beings should have results (even if errored)
        assert "forge" in results
        assert "scholar" in results
        # Cycle still counts as completed
        assert dc.status()["total_runs"] == 1


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dream log reporting
# ---------------------------------------------------------------------------

class TestDreamLogReporting:
    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_dream_log_written_after_cycle(self, mock_prov):
        """run_cycle() should write a markdown report to dream_logs/."""
        mock_provider = MagicMock()
        consolidate_resp = MagicMock(text=json.dumps({
            "duplicates": [{"keep": "mem_0", "remove": ["mem_1"]}],
            "contradictions": [], "stale": ["mem_2"],
        }))
        derive_resp = MagicMock(text=json.dumps([
            {"key": "derived::x", "content": "Test insight", "relevance_to_others": []},
        ]))
        mock_provider.generate.side_effect = [consolidate_resp, derive_resp]
        mock_prov.return_value = mock_provider

        dc, db, bridge, dashboard, tmpdir = _make_dream_cycle(with_memories=5, being_ids=["forge"])

        # Point dream logs to tmp dir
        log_dir = os.path.join(tmpdir, "dream_logs")
        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": tmpdir}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "dream_logs"):
                results = dc.run_cycle()

                # Verify log file was created
                assert os.path.isdir(log_dir)
                md_files = [f for f in os.listdir(log_dir) if f.endswith(".md")]
                assert len(md_files) == 1

                # Verify content
                content = Path(os.path.join(log_dir, md_files[0])).read_text()
                assert "Dream Cycle Report" in content
                assert "forge" in content
                assert "Duplicates removed:" in content

    @patch("bomba_sr.memory.dreaming.provider_from_env")
    def test_dream_log_contains_per_being_stats(self, mock_prov):
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = [
            # forge consolidate + derive
            MagicMock(text=json.dumps({"duplicates": [], "contradictions": [], "stale": []})),
            MagicMock(text=json.dumps([])),
            # scholar consolidate + derive
            MagicMock(text=json.dumps({"duplicates": [], "contradictions": [], "stale": []})),
            MagicMock(text=json.dumps([])),
        ]
        mock_prov.return_value = mock_provider

        dc, db, bridge, dashboard, tmpdir = _make_dream_cycle(with_memories=3, being_ids=["forge", "scholar"])

        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": tmpdir}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "dream_logs"):
                dc.run_cycle()

                log_dir = os.path.join(tmpdir, "dream_logs")
                md_files = [f for f in os.listdir(log_dir) if f.endswith(".md")]
                content = Path(os.path.join(log_dir, md_files[0])).read_text()
                # Both beings should appear
                assert "## Being: forge" in content
                assert "## Being: scholar" in content

    def test_dream_log_failure_does_not_crash_cycle(self):
        """If writing the log fails, the cycle still completes."""
        dc, *_ = _make_dream_cycle(being_ids=["forge"])
        dc.dashboard.get_being.return_value = None  # will skip all beings

        # Force a write error by pointing to invalid path
        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": "/nonexistent/path"}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "dream_logs"):
                results = dc.run_cycle()
                # Still completes
                assert dc.status()["total_runs"] == 1

    def test_list_dream_logs_returns_empty_when_no_dir(self):
        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": tempfile.mkdtemp()}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "nonexistent"):
                logs = DreamCycle.list_dream_logs()
                assert logs == []

    def test_list_dream_logs_returns_files(self):
        tmpdir = tempfile.mkdtemp()
        log_dir = os.path.join(tmpdir, "dream_logs")
        os.makedirs(log_dir)
        # Create 3 log files
        for i in range(3):
            Path(os.path.join(log_dir, f"2026-03-0{i+1}-12:00.md")).write_text(f"Log {i}")

        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": tmpdir}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "dream_logs"):
                logs = DreamCycle.list_dream_logs()
                assert len(logs) == 3
                # Newest first
                assert logs[0]["filename"] == "2026-03-03-12:00.md"

    def test_list_dream_logs_respects_limit(self):
        tmpdir = tempfile.mkdtemp()
        log_dir = os.path.join(tmpdir, "dream_logs")
        os.makedirs(log_dir)
        for i in range(5):
            Path(os.path.join(log_dir, f"2026-03-0{i+1}-12:00.md")).write_text(f"Log {i}")

        with patch.dict(os.environ, {"BOMBA_PROJECT_ROOT": tmpdir}):
            with patch("bomba_sr.memory.dreaming.DREAM_LOGS_DIR", "dream_logs"):
                logs = DreamCycle.list_dream_logs(limit=2)
                assert len(logs) == 2


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

class TestJsonParsing:
    def test_parse_clean_json(self):
        data = DreamCycle._parse_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_parse_fenced_json(self):
        data = DreamCycle._parse_json('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}

    def test_parse_array(self):
        data = DreamCycle._parse_json('[1, 2, 3]')
        assert data == [1, 2, 3]
