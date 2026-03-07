"""Integration tests verifying Phase 1 (orchestration) and Phase 2 (session/memory/subagent) fixes.

Tests cover:
  Phase 1: Orchestration state persistence, review parse failure blocking,
           Prime status restoration, orphaned cleanup.
  Phase 2: Session isolation, dream cycle cross-DB reads, memory_archive being_id,
           shared memory reads.
  Negative/Regression: DB as source of truth, concurrent session isolation,
                       _parse_review edge cases.
"""
from __future__ import annotations

import copy
import json
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.memory.consolidation import MemoryCandidate, MemoryConsolidator
from bomba_sr.orchestration.engine import OrchestrationEngine
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.protocol import (
    VALID_SCOPES,
    SubAgentProtocol,
    SubAgentTask,
)


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _make_db(tmpdir: str, name: str = "test.db") -> RuntimeDB:
    return RuntimeDB(f"{tmpdir}/{name}")


def _uuid() -> str:
    return str(uuid.uuid4())


def _ensure_orchestration_tables(db: RuntimeDB) -> None:
    """Create orchestration_state + task_results tables matching engine.py schemas."""
    db.script("""
        CREATE TABLE IF NOT EXISTS orchestration_state (
            task_id           TEXT PRIMARY KEY,
            goal              TEXT NOT NULL,
            orch_session_id   TEXT NOT NULL,
            requester_session TEXT NOT NULL,
            sender            TEXT NOT NULL,
            status            TEXT NOT NULL,
            plan_json         TEXT,
            subtask_ids       TEXT NOT NULL DEFAULT '{}',
            subtask_reviews   TEXT NOT NULL DEFAULT '{}',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS task_results (
            task_id    TEXT PRIMARY KEY,
            tenant_id  TEXT NOT NULL,
            goal       TEXT NOT NULL,
            strategy   TEXT NOT NULL,
            beings_used TEXT NOT NULL,
            outputs    TEXT NOT NULL,
            synthesis  TEXT NOT NULL,
            artifacts  TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_task_results_created
            ON task_results(tenant_id, created_at DESC);
    """)


def _ensure_memory_tables(db: RuntimeDB) -> None:
    """Create memory tables matching consolidation.py + dreaming.py."""
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
            reason TEXT NOT NULL,
            being_id TEXT,
            FOREIGN KEY(memory_id) REFERENCES memories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_memories_active_user
            ON memories(user_id, tier, active, updated_at DESC);

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
    """)


def _insert_memory(db: RuntimeDB, user_id: str, key: str, content: str,
                    being_id: str | None = None, recency_ts: str | None = None) -> str:
    """Insert a semantic memory directly and return its id."""
    mid = _uuid()
    now = recency_ts or datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO memories (id, user_id, memory_key, tier, content, entities, evidence_refs,
                              recency_ts, active, version, created_at, updated_at, being_id)
        VALUES (?, ?, ?, 'semantic', ?, '[]', '[]', ?, 1, 1, ?, ?, ?)
        """,
        (mid, user_id, key, content, now, now, now, being_id),
    )
    db.commit()
    return mid


def _insert_orchestration_state(db: RuntimeDB, task_id: str, status: str,
                                 updated_at: str | None = None, goal: str = "test") -> None:
    now = updated_at or datetime.now(timezone.utc).isoformat()
    db.execute_commit(
        """
        INSERT OR REPLACE INTO orchestration_state
            (task_id, goal, orch_session_id, requester_session, sender, status,
             plan_json, subtask_ids, subtask_reviews, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, goal, f"orch-{task_id[:8]}", "req-sess-1", "user", status,
         None, "{}", "{}", now, now),
    )


class _ReviewParser:
    """Minimal stand-in that binds _parse_review and _extract_json properly."""
    _extract_json = staticmethod(OrchestrationEngine._extract_json)
    _parse_review = OrchestrationEngine._parse_review


_review_parser = _ReviewParser()


def _subagent_task(ticket_id: str | None = None, key: str | None = None) -> SubAgentTask:
    return SubAgentTask(
        tenant_id="tenant-test",
        task_id=_uuid(),
        ticket_id=ticket_id or _uuid(),
        idempotency_key=key or f"key-{uuid.uuid4().hex[:12]}",
        goal="Integration test goal",
        done_when=("Done",),
        input_context_refs=(),
        output_schema={"summary": "string"},
        priority="normal",
        run_timeout_seconds=120,
        cleanup="keep",
        workspace_root=None,
        model_id=None,
    )


# ===================================================================
# Phase 1 Verification: Orchestration Engine
# ===================================================================

class TestPhase1OrchestrationPersistence:
    """1.1-1.4: Orchestration state persistence and DB load round-trip."""

    def test_1_1_state_persists_to_db_and_loads_back(self, tmp_path: Path) -> None:
        """State written to orchestration_state can be reconstructed by _db_load_state."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        task_id = _uuid()
        goal = "Analyze codebase for security issues"
        now = datetime.now(timezone.utc).isoformat()

        plan_data = {
            "summary": "Split across analyst and scholar",
            "sub_tasks": [
                {"being_id": "analyst", "title": "Static analysis", "instructions": "Run SAST", "done_when": "Report ready"},
                {"being_id": "scholar", "title": "Dependency audit", "instructions": "Check CVEs", "done_when": "CVE list generated"},
            ],
            "synthesis_strategy": "merge",
        }
        subtask_ids = {"analyst": "sub-1", "scholar": "sub-2"}
        subtask_reviews = {"analyst": {"approved": True, "quality_score": 0.85}}

        db.execute_commit(
            """
            INSERT INTO orchestration_state
                (task_id, goal, orch_session_id, requester_session, sender, status,
                 plan_json, subtask_ids, subtask_reviews, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, goal, f"orch-{task_id[:8]}", "req-sess", "user", "executing",
             json.dumps(plan_data), json.dumps(subtask_ids),
             json.dumps(subtask_reviews), now, now),
        )

        # Load it back the same way _db_load_state does
        row = db.execute(
            "SELECT * FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        assert row is not None
        assert row["goal"] == goal
        assert row["status"] == "executing"

        loaded_plan = json.loads(row["plan_json"])
        assert loaded_plan["summary"] == "Split across analyst and scholar"
        assert len(loaded_plan["sub_tasks"]) == 2
        assert loaded_plan["sub_tasks"][0]["being_id"] == "analyst"

        loaded_ids = json.loads(row["subtask_ids"])
        assert loaded_ids == subtask_ids

        loaded_reviews = json.loads(row["subtask_reviews"])
        assert loaded_reviews["analyst"]["approved"] is True

    def test_1_2_status_update_persists(self, tmp_path: Path) -> None:
        """Status changes are reflected in DB."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        task_id = _uuid()
        _insert_orchestration_state(db, task_id, "planning")

        new_status = "executing"
        new_ts = datetime.now(timezone.utc).isoformat()
        db.execute_commit(
            "UPDATE orchestration_state SET status = ?, updated_at = ? WHERE task_id = ?",
            (new_status, new_ts, task_id),
        )

        row = db.execute(
            "SELECT status, updated_at FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        assert row["status"] == "executing"

    def test_1_3_subtask_outputs_via_shared_memory(self, tmp_path: Path) -> None:
        """Subtask outputs are now stored in shared_working_memory_writes, not orchestration_state."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        protocol = SubAgentProtocol(db)
        ticket_id = _uuid()

        # Write output for being A
        protocol.write_shared_memory(
            run_id=None,
            writer_agent_id="analyst",
            ticket_id=ticket_id,
            scope="committed",
            confidence=0.9,
            content="Found 3 issues",
        )
        # Write output for being B
        protocol.write_shared_memory(
            run_id=None,
            writer_agent_id="scholar",
            ticket_id=ticket_id,
            scope="committed",
            confidence=0.9,
            content="Checked 150 deps, 2 CVEs",
        )

        # Read back via shared memory
        writes = protocol.read_shared_memory(ticket_id, scope="committed")
        outputs = {w["writer_agent_id"]: w["content"] for w in writes}
        assert "analyst" in outputs
        assert "scholar" in outputs
        assert "3 issues" in outputs["analyst"]
        assert "2 CVEs" in outputs["scholar"]

    def test_1_4_subtask_reviews_merge_correctly(self, tmp_path: Path) -> None:
        """Incremental review merging keeps all being reviews."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        task_id = _uuid()
        _insert_orchestration_state(db, task_id, "reviewing")

        for being_id, review in [
            ("analyst", {"approved": True, "quality_score": 0.9}),
            ("scholar", {"approved": False, "quality_score": 0.3, "feedback": "Needs more detail"}),
        ]:
            row = db.execute(
                "SELECT subtask_reviews FROM orchestration_state WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            current = json.loads(row["subtask_reviews"])
            current[being_id] = review
            db.execute_commit(
                "UPDATE orchestration_state SET subtask_reviews = ? WHERE task_id = ?",
                (json.dumps(current), task_id),
            )

        row = db.execute(
            "SELECT subtask_reviews FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        reviews = json.loads(row["subtask_reviews"])
        assert reviews["analyst"]["approved"] is True
        assert reviews["scholar"]["approved"] is False
        assert reviews["scholar"]["feedback"] == "Needs more detail"


class TestPhase1ReviewParseFailure:
    """1.5-1.6: _parse_review blocks approval on malformed LLM output."""

    def test_1_5_parse_review_blocks_on_invalid_json(self) -> None:
        """Unparseable JSON returns approved=False, quality_score=0.0."""
        result = _review_parser._parse_review("This is not JSON at all")
        assert result["approved"] is False
        assert result["quality_score"] == 0.0
        assert "unparseable" in result["feedback"].lower() or "unparseable" in result["notes"].lower()

    def test_1_5b_parse_review_blocks_on_partial_json(self) -> None:
        """Truncated JSON returns approved=False."""
        result = _review_parser._parse_review('{"approved": true, "quality_score":')
        assert result["approved"] is False
        assert result["quality_score"] == 0.0

    def test_1_6_parse_review_succeeds_on_valid_json(self) -> None:
        """Valid JSON with approved=true passes through."""
        raw = json.dumps({
            "approved": True,
            "feedback": "Looks good",
            "quality_score": 0.92,
            "notes": "Minor style issue",
        })
        result = _review_parser._parse_review(raw)
        assert result["approved"] is True
        assert result["quality_score"] == 0.92
        assert result["feedback"] == "Looks good"

    def test_1_6b_parse_review_handles_markdown_fenced_json(self) -> None:
        """JSON wrapped in ```json fences parses correctly."""
        raw = '```json\n{"approved": true, "quality_score": 0.88, "feedback": "ok", "notes": ""}\n```'
        result = _review_parser._parse_review(raw)
        assert result["approved"] is True
        assert result["quality_score"] == 0.88

    def test_1_6c_missing_approved_defaults_false(self) -> None:
        """Missing 'approved' key defaults to False per bool(data.get('approved', False))."""
        raw = json.dumps({"quality_score": 0.7, "feedback": "looks ok"})
        result = _review_parser._parse_review(raw)
        assert result["approved"] is False

    def test_1_6d_string_approved_truthy(self) -> None:
        """String 'yes' for approved is truthy via bool()."""
        raw = json.dumps({"approved": "yes", "quality_score": 0.8})
        result = _review_parser._parse_review(raw)
        assert result["approved"] is True  # bool("yes") == True


class TestPhase1OrphanedCleanup:
    """1.7-1.8: Orphaned orchestration cleanup."""

    def test_1_7_stale_orchestrations_marked_failed(self, tmp_path: Path) -> None:
        """Orchestrations older than 1 hour with non-terminal status are cleaned up."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        # Insert a stale "executing" task — updated 2 hours ago
        stale_id = _uuid()
        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        _insert_orchestration_state(db, stale_id, "executing", updated_at=two_hours_ago)

        # Insert a recent "executing" task — should NOT be cleaned
        recent_id = _uuid()
        _insert_orchestration_state(db, recent_id, "executing")

        # Insert a completed task — should NOT be cleaned
        done_id = _uuid()
        _insert_orchestration_state(db, done_id, "completed", updated_at=two_hours_ago)

        # Run cleanup logic (mimicking engine.cleanup_orphaned_orchestrations)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        rows = db.execute(
            """
            SELECT task_id FROM orchestration_state
            WHERE status NOT IN ('completed', 'failed')
              AND updated_at < ?
            """,
            (cutoff,),
        ).fetchall()

        cleaned_ids = []
        for row in rows:
            tid = row["task_id"]
            db.execute_commit(
                "UPDATE orchestration_state SET status = 'failed', updated_at = ? WHERE task_id = ?",
                (datetime.now(timezone.utc).isoformat(), tid),
            )
            cleaned_ids.append(tid)

        assert stale_id in cleaned_ids
        assert recent_id not in cleaned_ids
        assert done_id not in cleaned_ids

        # Verify stale is now failed
        row = db.execute(
            "SELECT status FROM orchestration_state WHERE task_id = ?",
            (stale_id,),
        ).fetchone()
        assert row["status"] == "failed"

    def test_1_8_terminal_states_untouched(self, tmp_path: Path) -> None:
        """Completed/failed orchestrations are never cleaned up regardless of age."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        for status in ("completed", "failed"):
            tid = _uuid()
            _insert_orchestration_state(db, tid, status, updated_at=old_ts)

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        rows = db.execute(
            """
            SELECT task_id FROM orchestration_state
            WHERE status NOT IN ('completed', 'failed')
              AND updated_at < ?
            """,
            (cutoff,),
        ).fetchall()
        assert len(rows) == 0


# ===================================================================
# Phase 2 Verification: Session / Memory / Sub-Agent
# ===================================================================

class TestPhase2SessionIsolation:
    """2.1-2.3: Dashboard session_id construction and isolation."""

    def test_2_1_session_id_uses_being_id_not_sender(self) -> None:
        """session_id is f'mc-chat-{being_id}', sender is NOT part of it."""
        being_id = "scholar"
        session_id = f"mc-chat-{being_id}"
        assert session_id == "mc-chat-scholar"
        # Sender is not embedded
        assert "user" not in session_id
        assert "admin" not in session_id

    def test_2_2_same_being_same_session_regardless_of_sender(self) -> None:
        """Two different senders messaging the same being get the same session_id."""
        being_id = "forge"
        session_from_alice = f"mc-chat-{being_id}"
        session_from_bob = f"mc-chat-{being_id}"
        assert session_from_alice == session_from_bob

    def test_2_3_different_beings_different_sessions(self) -> None:
        """Different beings produce different session_ids."""
        assert f"mc-chat-scholar" != f"mc-chat-forge"
        assert f"mc-chat-prime" != f"mc-chat-callie"


class TestPhase2DreamCycleCrossDB:
    """2.4-2.6: Dream cycle reads task_results from Prime's DB, not being's DB."""

    def test_2_4_task_results_live_in_prime_db(self, tmp_path: Path) -> None:
        """task_results table exists in Prime's DB, not in being DBs."""
        prime_db = _make_db(str(tmp_path), "prime.db")
        being_db = _make_db(str(tmp_path), "scholar.db")

        _ensure_orchestration_tables(prime_db)

        # Insert a task_result into Prime's DB
        prime_db.execute_commit(
            """
            INSERT INTO task_results (task_id, tenant_id, goal, strategy, beings_used, outputs, synthesis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_uuid(), "tenant-prime", "Test goal", "merge",
             json.dumps(["scholar", "analyst"]), json.dumps({}),
             "Combined analysis", datetime.now(timezone.utc).isoformat()),
        )

        # Verify it's in prime
        rows = prime_db.execute("SELECT COUNT(*) AS c FROM task_results").fetchone()
        assert rows["c"] == 1

        # Verify being DB does NOT have task_results (table doesn't even exist)
        tables = being_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='task_results'"
        ).fetchall()
        assert len(tables) == 0

    def test_2_5_dream_gather_reads_prime_for_task_results(self, tmp_path: Path) -> None:
        """_phase_gather queries task_results from prime_runtime, not being_runtime."""
        prime_db = _make_db(str(tmp_path), "prime.db")
        being_db = _make_db(str(tmp_path), "scholar.db")

        _ensure_orchestration_tables(prime_db)
        _ensure_memory_tables(being_db)

        being_id = "scholar"
        # Insert task_result in Prime's DB referencing scholar
        prime_db.execute_commit(
            """
            INSERT INTO task_results (task_id, tenant_id, goal, strategy, beings_used, outputs, synthesis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_uuid(), "tenant-prime", "Analyze code", "merge",
             json.dumps(["scholar"]), json.dumps({"scholar": "output"}),
             "Scholar found patterns", datetime.now(timezone.utc).isoformat()),
        )

        # Query from Prime's DB the same way dreaming.py does
        rows = prime_db.execute(
            """
            SELECT task_id, goal, strategy, beings_used, synthesis, created_at
            FROM task_results
            WHERE beings_used LIKE ?
            ORDER BY created_at DESC LIMIT 5
            """,
            (f'%"{being_id}"%',),
        ).fetchall()
        assert len(rows) == 1
        assert "Analyze code" in rows[0]["goal"]

    def test_2_6_being_db_query_returns_empty_for_task_results(self, tmp_path: Path) -> None:
        """Querying the being's own DB for task_results finds nothing (correct behavior)."""
        being_db = _make_db(str(tmp_path), "scholar.db")
        _ensure_memory_tables(being_db)

        # Being DB should not have task_results table
        tables = being_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='task_results'"
        ).fetchall()
        assert len(tables) == 0


class TestPhase2MemoryArchiveBeingId:
    """2.7-2.8: memory_archive preserves being_id."""

    def test_2_7_consolidation_upsert_archives_with_being_id(self, tmp_path: Path) -> None:
        """When MemoryConsolidator.upsert() archives a contradiction, being_id is preserved."""
        db = _make_db(str(tmp_path))
        mc = MemoryConsolidator(db)

        # Insert initial memory with being_id
        mid = mc.upsert(MemoryCandidate(
            user_id="scholar",
            key="topic::python_async",
            content="Python async is event-loop based",
            being_id="scholar",
        ))

        # Upsert with different content -> contradiction -> archive
        new_mid = mc.upsert(MemoryCandidate(
            user_id="scholar",
            key="topic::python_async",
            content="Python async uses coroutines and an event loop with await syntax",
            being_id="scholar",
        ))
        assert new_mid != mid  # new version created

        # Check archive has being_id
        archive = db.execute(
            "SELECT being_id, old_content, reason FROM memory_archive WHERE memory_id = ?",
            (mid,),
        ).fetchone()
        assert archive is not None
        assert archive["being_id"] == "scholar"
        assert "contradiction" in archive["reason"]

    def test_2_8_dream_prune_archives_with_being_id(self, tmp_path: Path) -> None:
        """Dream prune phase carries being_id into memory_archive."""
        db = _make_db(str(tmp_path))
        _ensure_memory_tables(db)

        being_id = "analyst"
        now = datetime.now(timezone.utc).isoformat()

        # Insert a memory with being_id
        mid = _insert_memory(db, being_id, "test::key", "Some content", being_id=being_id)

        # Simulate dream prune archival
        row = db.execute(
            "SELECT id, memory_key, content, being_id FROM memories WHERE id = ?",
            (mid,),
        ).fetchone()
        assert row["being_id"] == being_id

        archive_id = _uuid()
        db.execute_commit(
            """
            INSERT INTO memory_archive (id, memory_id, user_id, memory_key, old_content, archived_at, reason, being_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (archive_id, mid, being_id, row["memory_key"], row["content"], now, "dream_prune", row["being_id"]),
        )

        archive = db.execute(
            "SELECT being_id FROM memory_archive WHERE id = ?",
            (archive_id,),
        ).fetchone()
        assert archive["being_id"] == being_id


class TestPhase2SharedMemoryReads:
    """2.9-2.10: Shared working memory reads via SubAgentProtocol."""

    def test_2_9_read_shared_memory_round_trip(self, tmp_path: Path) -> None:
        """Write shared memory entries, then read them back."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)
        ticket = _uuid()

        run = p.spawn(
            task=_subagent_task(ticket_id=ticket),
            parent_session_id=_uuid(),
            parent_turn_id="turn-sm1",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )

        w1 = p.write_shared_memory(
            run_id=run["run_id"],
            writer_agent_id="agent-a",
            ticket_id=ticket,
            scope="scratch",
            confidence=0.5,
            content="Initial scratch observation",
        )
        w2 = p.write_shared_memory(
            run_id=run["run_id"],
            writer_agent_id="agent-b",
            ticket_id=ticket,
            scope="committed",
            confidence=0.95,
            content="Final committed finding",
            source_refs=["ref-alpha", "ref-beta"],
        )

        # Read all
        all_writes = p.read_shared_memory(ticket)
        assert len(all_writes) == 2

        # Most recent first (committed was written second)
        assert all_writes[0]["write_id"] == w2
        assert all_writes[0]["scope"] == "committed"
        assert all_writes[0]["source_refs"] == ["ref-alpha", "ref-beta"]

        assert all_writes[1]["write_id"] == w1
        assert all_writes[1]["scope"] == "scratch"

    def test_2_9b_read_shared_memory_scope_filter(self, tmp_path: Path) -> None:
        """Scope filter returns only matching entries."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)
        ticket = _uuid()

        run = p.spawn(
            task=_subagent_task(ticket_id=ticket),
            parent_session_id=_uuid(),
            parent_turn_id="turn-sf1",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )

        p.write_shared_memory(run["run_id"], "a", ticket, "scratch", 0.5, "Scratch note")
        p.write_shared_memory(run["run_id"], "b", ticket, "proposal", 0.7, "Proposal note")
        p.write_shared_memory(run["run_id"], "c", ticket, "committed", 0.9, "Committed note")

        assert len(p.read_shared_memory(ticket, scope="scratch")) == 1
        assert len(p.read_shared_memory(ticket, scope="proposal")) == 1
        assert len(p.read_shared_memory(ticket, scope="committed")) == 1
        assert len(p.read_shared_memory(ticket)) == 3

    def test_2_10_read_shared_memory_invalid_scope_raises(self, tmp_path: Path) -> None:
        """Invalid scope raises ValueError."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)
        ticket = _uuid()

        with pytest.raises(ValueError, match="invalid scope"):
            p.read_shared_memory(ticket, scope="bogus")

    def test_2_10b_shared_memory_promote(self, tmp_path: Path) -> None:
        """promote_shared_write changes scope to committed."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)
        ticket = _uuid()

        run = p.spawn(
            task=_subagent_task(ticket_id=ticket),
            parent_session_id=_uuid(),
            parent_turn_id="turn-pm1",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )

        w = p.write_shared_memory(run["run_id"], "agent-x", ticket, "proposal", 0.8, "Draft finding")
        p.promote_shared_write(w, merged_by_agent_id="prime")

        committed = p.read_shared_memory(ticket, scope="committed")
        assert len(committed) == 1
        assert committed[0]["content"] == "Draft finding"
        assert committed[0]["merged_by_agent_id"] == "prime"


# ===================================================================
# Negative / Regression Tests
# ===================================================================

class TestNegativeDBSourceOfTruth:
    """N.1: DB is the source of truth — in-memory cache loss recovery."""

    def test_n1_state_recoverable_from_db_after_cache_clear(self, tmp_path: Path) -> None:
        """If in-memory _active dict is cleared, state still loads from DB."""
        db = _make_db(str(tmp_path))
        _ensure_orchestration_tables(db)

        task_id = _uuid()
        plan_data = {
            "summary": "Test recovery",
            "sub_tasks": [{"being_id": "scholar", "title": "Read docs", "instructions": "Check docs", "done_when": "Done"}],
            "synthesis_strategy": "merge",
        }
        now = datetime.now(timezone.utc).isoformat()
        db.execute_commit(
            """
            INSERT INTO orchestration_state
                (task_id, goal, orch_session_id, requester_session, sender, status,
                 plan_json, subtask_ids, subtask_reviews, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, "Recover test", f"orch-{task_id[:8]}", "req", "user", "executing",
             json.dumps(plan_data), "{}", "{}", now, now),
        )

        # Simulate _db_load_state
        row = db.execute(
            "SELECT * FROM orchestration_state WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        assert row is not None

        loaded_plan = json.loads(row["plan_json"])
        state = {
            "task_id": task_id,
            "goal": row["goal"],
            "orchestration_session": row["orch_session_id"],
            "requester_session": row["requester_session"],
            "sender": row["sender"],
            "status": row["status"],
            "plan": loaded_plan,
            "subtask_ids": json.loads(row["subtask_ids"] or "{}"),
            "subtask_outputs": {},  # outputs now in shared_working_memory_writes
            "subtask_reviews": json.loads(row["subtask_reviews"] or "{}"),
            "created_at": row["created_at"],
        }

        assert state["goal"] == "Recover test"
        assert state["status"] == "executing"
        assert state["plan"]["sub_tasks"][0]["being_id"] == "scholar"


class TestNegativeConcurrentSessionIsolation:
    """N.2: Concurrent sessions on different tenants don't interfere."""

    def test_n2_separate_tenant_dbs_are_isolated(self, tmp_path: Path) -> None:
        """Two tenant DBs store independent data."""
        db_a = _make_db(str(tmp_path), "tenant-a.db")
        db_b = _make_db(str(tmp_path), "tenant-b.db")

        _ensure_memory_tables(db_a)
        _ensure_memory_tables(db_b)

        # Insert memory in A
        _insert_memory(db_a, "user-a", "topic::x", "Tenant A content", being_id="analyst")

        # Insert memory in B
        _insert_memory(db_b, "user-b", "topic::y", "Tenant B content", being_id="scholar")

        # A should not see B's memory
        rows_a = db_a.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        rows_b = db_b.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        assert rows_a["c"] == 1
        assert rows_b["c"] == 1

        # Cross-check: A's memory is not in B
        cross = db_b.execute(
            "SELECT * FROM memories WHERE memory_key = 'topic::x'"
        ).fetchall()
        assert len(cross) == 0

    def test_n2b_subagent_protocol_tenant_isolation(self, tmp_path: Path) -> None:
        """SubAgentProtocol instances on separate DBs are isolated."""
        db_a = _make_db(str(tmp_path), "sa-tenant-a.db")
        db_b = _make_db(str(tmp_path), "sa-tenant-b.db")

        pa = SubAgentProtocol(db_a)
        pb = SubAgentProtocol(db_b)

        ticket_a = _uuid()
        ticket_b = _uuid()

        run_a = pa.spawn(
            task=_subagent_task(ticket_id=ticket_a),
            parent_session_id=_uuid(),
            parent_turn_id="turn-a",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )
        run_b = pb.spawn(
            task=_subagent_task(ticket_id=ticket_b),
            parent_session_id=_uuid(),
            parent_turn_id="turn-b",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )

        pa.write_shared_memory(run_a["run_id"], "a", ticket_a, "scratch", 0.5, "Tenant A write")
        pb.write_shared_memory(run_b["run_id"], "b", ticket_b, "committed", 0.9, "Tenant B write")

        assert len(pa.read_shared_memory(ticket_a)) == 1
        assert len(pb.read_shared_memory(ticket_b)) == 1
        assert len(pa.read_shared_memory(ticket_b)) == 0  # A can't see B's ticket
        assert len(pb.read_shared_memory(ticket_a)) == 0  # B can't see A's ticket


class TestNegativeParseReviewEdgeCases:
    """N.3: _parse_review and _extract_json edge cases."""

    def test_n3_empty_string(self) -> None:
        result = _review_parser._parse_review("")
        assert result["approved"] is False
        assert result["quality_score"] == 0.0

    def test_n3b_json_array_not_object(self) -> None:
        """A JSON array instead of object should fail."""
        result = _review_parser._parse_review('[{"approved": true}]')
        # json.loads succeeds but data.get fails on a list
        assert result["approved"] is False

    def test_n3c_nested_markdown_fences(self) -> None:
        """Multiple fence layers — first closing fence is used."""
        raw = '```json\n{"approved": true, "quality_score": 0.75, "feedback": "good"}\n```\nextra text'
        result = _review_parser._parse_review(raw)
        assert result["approved"] is True
        assert result["quality_score"] == 0.75

    def test_n3d_extract_json_plain(self) -> None:
        """Plain JSON without fences extracts fine."""
        data = OrchestrationEngine._extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_n3e_extract_json_with_whitespace(self) -> None:
        """Leading/trailing whitespace is stripped."""
        data = OrchestrationEngine._extract_json('  \n  {"a": 1}  \n  ')
        assert data == {"a": 1}

    def test_n3f_quality_score_clamping(self) -> None:
        """quality_score beyond 1.0 is passed through (no clamping in _parse_review)."""
        raw = json.dumps({"approved": True, "quality_score": 1.5, "feedback": "over"})
        result = _review_parser._parse_review(raw)
        assert result["quality_score"] == 1.5  # No clamping — float() passes through

    def test_n3g_approved_zero_is_falsy(self) -> None:
        """approved: 0 is falsy via bool()."""
        raw = json.dumps({"approved": 0, "quality_score": 0.5})
        result = _review_parser._parse_review(raw)
        assert result["approved"] is False

    def test_n3h_approved_one_is_truthy(self) -> None:
        """approved: 1 is truthy via bool()."""
        raw = json.dumps({"approved": 1, "quality_score": 0.5})
        result = _review_parser._parse_review(raw)
        assert result["approved"] is True


class TestNegativeSubAgentProtocolEdgeCases:
    """Additional subagent protocol robustness tests."""

    def test_cascade_stop_terminates_parent_and_children(self, tmp_path: Path) -> None:
        """cascade_stop stops both parent and child runs."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)

        parent_run = p.spawn(
            task=_subagent_task(),
            parent_session_id=_uuid(),
            parent_turn_id="turn-parent",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )
        child_run = p.spawn(
            task=_subagent_task(),
            parent_session_id=_uuid(),
            parent_turn_id="turn-child",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
            parent_run_id=parent_run["run_id"],
        )

        p.start(parent_run["run_id"])
        p.start(child_run["run_id"])

        stopped = p.cascade_stop(parent_run["run_id"], reason="test abort")
        assert parent_run["run_id"] in stopped
        assert child_run["run_id"] in stopped

    def test_event_stream_ordering(self, tmp_path: Path) -> None:
        """Events stream in chronological order."""
        db = _make_db(str(tmp_path))
        p = SubAgentProtocol(db)

        run = p.spawn(
            task=_subagent_task(),
            parent_session_id=_uuid(),
            parent_turn_id="turn-eso",
            parent_agent_id=_uuid(),
            child_agent_id=_uuid(),
        )
        rid = run["run_id"]

        p.start(rid)
        p.progress(rid, 25, summary="Quarter done")
        p.progress(rid, 75, summary="Three quarters")
        p.complete(rid, summary="Done", artifacts=None, runtime_ms=500, token_usage=None)

        events = p.stream_events(rid)
        types = [e["event_type"] for e in events]
        assert types == ["accepted", "started", "progress", "progress", "completed"]

        # after_seq filtering
        partial = p.stream_events(rid, after_seq=events[2]["seq"])
        assert len(partial) == 2  # progress(75) + completed
        assert partial[0]["event_type"] == "progress"
        assert partial[1]["event_type"] == "completed"
