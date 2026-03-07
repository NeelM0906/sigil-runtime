"""Tests for embedding-based similarity scoring in being-scoped memory recall.

Verifies that _recall_markdown_by_being() uses embedding scores when an
embedding provider is available, matching the behavior of _recall_markdown().
"""
from __future__ import annotations

import inspect
import json
import math
import tempfile
import textwrap
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from bomba_sr.memory.hybrid import HybridMemoryStore
from bomba_sr.storage.db import RuntimeDB


class _FakeEmbeddingProvider:
    """Deterministic embedding provider for tests."""

    model = "test-embed-model"

    def __init__(self, vectors: dict[str, list[float]] | None = None):
        # Map text -> vector for deterministic results
        self._vectors = vectors or {}
        self._default = [0.0, 0.0, 1.0]
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self._vectors.get(t, self._default) for t in texts]


def _make_store(td: str, embedding_provider=None):
    db = RuntimeDB(f"{td}/runtime.db")
    store = HybridMemoryStore(
        db=db,
        memory_root=Path(td) / "memory",
        auto_apply_confidence=0.4,
        embedding_provider=embedding_provider,
    )
    return store, db


def _save_note(store, being_id, title, content, user_id="user-1", session_id="sess-1"):
    return store.append_working_note(
        user_id=user_id,
        session_id=session_id,
        title=title,
        content=content,
        being_id=being_id,
    )


class TestBeingEmbeddingRecall:
    """_recall_markdown_by_being uses embeddings when provider is available."""

    def test_embedding_scores_used_when_provider_present(self):
        """Notes are ranked by embedding similarity, not just lexical."""
        # Vectors: query is [1,0,0], note1 is orthogonal [0,1,0], note2 is aligned [0.9,0.1,0]
        provider = _FakeEmbeddingProvider(vectors={
            "find aligned content": [1.0, 0.0, 0.0],
            "This note is orthogonal and unrelated": [0.0, 1.0, 0.0],
            "This note is aligned with the query": [0.9, 0.1, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            _save_note(store, "scholar", "Orthogonal Note", "This note is orthogonal and unrelated")
            _save_note(store, "scholar", "Aligned Note", "This note is aligned with the query")

            results = store._recall_markdown_by_being("scholar", "find aligned content", limit=10)

            assert len(results) == 2
            # Aligned note should rank first by embedding score
            assert results[0]["title"] == "Aligned Note"
            assert results[1]["title"] == "Orthogonal Note"
            assert results[0]["score"] > results[1]["score"]

    def test_lexical_fallback_when_no_provider(self):
        """Without embedding provider, falls back to lexical scoring."""
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=None)
            _save_note(store, "scholar", "Python Guide", "Python programming best practices guide")
            _save_note(store, "scholar", "Unrelated", "Cooking recipes for pasta")

            results = store._recall_markdown_by_being("scholar", "python programming", limit=10)

            assert len(results) == 2
            # Lexical match: "Python" appears in first note
            assert results[0]["title"] == "Python Guide"

    def test_embedding_scores_scoped_to_being(self):
        """Only notes owned by the queried being are scored/returned."""
        provider = _FakeEmbeddingProvider(vectors={
            "search query": [1.0, 0.0, 0.0],
            "Scholar note content": [0.9, 0.1, 0.0],
            "Forge note content": [0.95, 0.05, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            _save_note(store, "scholar", "Scholar Note", "Scholar note content")
            _save_note(store, "forge", "Forge Note", "Forge note content")

            results = store._recall_markdown_by_being("scholar", "search query", limit=10)

            assert len(results) == 1
            assert results[0]["title"] == "Scholar Note"

    def test_lexical_used_for_notes_without_embeddings(self):
        """Notes saved without embedding (manually inserted) use lexical scoring."""
        provider = _FakeEmbeddingProvider(vectors={
            "search term": [1.0, 0.0, 0.0],
            "Embedded note text": [0.8, 0.2, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            # Save one note normally (gets embedding)
            _save_note(store, "scholar", "Embedded", "Embedded note text")

            # Manually insert a note without embedding
            note_id = str(uuid.uuid4())
            rel_path = f"notes/{note_id}.md"
            abs_path = Path(td) / "memory" / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text("---\n{}\n---\n\nsearch term appears here", encoding="utf-8")
            db.execute(
                """
                INSERT INTO markdown_notes (note_id, user_id, session_id, relative_path, title,
                  tags, confidence, created_at, being_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, "user-1", "sess-1", rel_path, "Manual Note",
                 "[]", 1.0, "2025-01-01T00:00:00", "scholar"),
            )
            db.commit()

            results = store._recall_markdown_by_being("scholar", "search term", limit=10)

            assert len(results) == 2
            titles = [r["title"] for r in results]
            assert "Manual Note" in titles
            assert "Embedded" in titles

    def test_empty_being_returns_empty(self):
        """No notes for being returns empty list."""
        provider = _FakeEmbeddingProvider()
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            results = store._recall_markdown_by_being("nonexistent", "query", limit=10)
            assert results == []

    def test_embedding_provider_called_once(self):
        """Embedding provider is called exactly once for the query."""
        provider = _FakeEmbeddingProvider(vectors={
            "test query": [1.0, 0.0, 0.0],
            "note content": [0.5, 0.5, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            _save_note(store, "scholar", "Note", "note content")

            # Clear call history from save
            provider.calls.clear()

            store._recall_markdown_by_being("scholar", "test query", limit=10)

            # Should call embed once with the query
            assert len(provider.calls) == 1
            assert provider.calls[0] == ["test query"]


class TestEmbeddingScoresByBeing:
    """Direct tests for _embedding_scores_by_being method."""

    def test_returns_empty_when_no_provider(self):
        with tempfile.TemporaryDirectory() as td:
            store, _ = _make_store(td, embedding_provider=None)
            assert store._embedding_scores_by_being("scholar", "query") == {}

    def test_returns_empty_when_no_embeddings_for_being(self):
        provider = _FakeEmbeddingProvider()
        with tempfile.TemporaryDirectory() as td:
            store, _ = _make_store(td, embedding_provider=provider)
            assert store._embedding_scores_by_being("scholar", "query") == {}

    def test_scores_only_include_being_notes(self):
        """Embeddings from other beings are excluded."""
        provider = _FakeEmbeddingProvider(vectors={
            "query text": [1.0, 0.0, 0.0],
            "Scholar content": [0.8, 0.2, 0.0],
            "Forge content": [0.9, 0.1, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, _ = _make_store(td, embedding_provider=provider)
            scholar_note = _save_note(store, "scholar", "S", "Scholar content")
            forge_note = _save_note(store, "forge", "F", "Forge content")

            provider.calls.clear()
            scores = store._embedding_scores_by_being("scholar", "query text")

            assert scholar_note["note_id"] in scores
            assert forge_note["note_id"] not in scores


# ---------------------------------------------------------------------------
# Phase 5.2 verification tests (exact names from spec)
# ---------------------------------------------------------------------------

class TestPhase52Verification:
    """Phase 5.2 acceptance tests — exact names from spec."""

    def test_recall_by_being_uses_embeddings_when_available(self):
        """Verify _embedding_scores_by_being is called and results are re-ranked."""
        provider = _FakeEmbeddingProvider(vectors={
            "test query": [1.0, 0.0, 0.0],
            # Lexically both have "note" but embedding distances differ
            "First note stored early": [0.1, 0.9, 0.0],   # far from query
            "Second note stored later": [0.95, 0.05, 0.0],  # close to query
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            _save_note(store, "scholar", "First", "First note stored early")
            _save_note(store, "scholar", "Second", "Second note stored later")

            with patch.object(
                store, "_embedding_scores_by_being", wraps=store._embedding_scores_by_being
            ) as spy:
                results = store._recall_markdown_by_being("scholar", "test query", limit=10)

                # Spy was called
                spy.assert_called_once_with(being_id="scholar", query="test query")

            # Embedding-based re-ranking: Second is closer to query vector
            assert len(results) == 2
            assert results[0]["title"] == "Second"
            assert results[0]["score"] > results[1]["score"]

    def test_recall_by_being_lexical_only_without_embeddings(self):
        """No embedding provider → pure lexical, no embedding calls."""
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=None)
            _save_note(store, "scholar", "Python Tips", "Python programming tips and tricks")
            _save_note(store, "scholar", "Cooking", "How to cook pasta al dente")

            with patch.object(
                store, "_embedding_scores_by_being", wraps=store._embedding_scores_by_being
            ) as spy:
                results = store._recall_markdown_by_being("scholar", "python programming", limit=10)

                # Called but returns {} immediately (provider is None)
                spy.assert_called_once()

            # Results returned via lexical
            assert len(results) == 2
            assert results[0]["title"] == "Python Tips"
            # No embedding provider means _embedding_scores_by_being returns {}
            assert store._embedding_scores_by_being("scholar", "anything") == {}

    def test_embedding_scores_by_being_filters_correctly(self):
        """Only scholar's note_ids in returned dict, not forge's."""
        provider = _FakeEmbeddingProvider(vectors={
            "test": [1.0, 0.0, 0.0],
            "Scholar data": [0.8, 0.2, 0.0],
            "Forge data": [0.9, 0.1, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            scholar_note = _save_note(store, "scholar", "S", "Scholar data")
            forge_note = _save_note(store, "forge", "F", "Forge data")

            provider.calls.clear()
            scores = store._embedding_scores_by_being("scholar", "test")

            assert scholar_note["note_id"] in scores
            assert forge_note["note_id"] not in scores
            assert len(scores) == 1

    def test_embedding_scores_by_being_empty_when_no_embeddings(self):
        """Notes exist for being but no embedding rows → empty dict, no crash."""
        provider = _FakeEmbeddingProvider()
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)

            # Insert note directly into DB without embedding row
            note_id = str(uuid.uuid4())
            rel_path = f"notes/{note_id}.md"
            abs_path = Path(td) / "memory" / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text("---\n{}\n---\n\nsome content", encoding="utf-8")
            db.execute(
                """
                INSERT INTO markdown_notes (note_id, user_id, session_id, relative_path, title,
                  tags, confidence, created_at, being_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, "user-1", "sess-1", rel_path, "No Embedding Note",
                 "[]", 1.0, "2025-01-01T00:00:00", "scholar"),
            )
            db.commit()

            # Verify note exists for scholar
            rows = db.execute(
                "SELECT note_id FROM markdown_notes WHERE being_id = ?", ("scholar",)
            ).fetchall()
            assert len(rows) == 1

            # But no embedding rows for it
            scores = store._embedding_scores_by_being("scholar", "query")
            assert scores == {}

    def test_recall_by_being_score_weights_match_recall_by_user(self):
        """The scoring logic in _recall_markdown_by_being matches _recall_markdown exactly.

        Both methods use embedding score when available, else lexical — no
        weighted blend. We verify by running both on identical data and
        comparing the resulting scores.
        """
        provider = _FakeEmbeddingProvider(vectors={
            "search query": [1.0, 0.0, 0.0],
            "Note A content": [0.9, 0.1, 0.0],
            "Note B content": [0.3, 0.7, 0.0],
        })
        with tempfile.TemporaryDirectory() as td:
            store, db = _make_store(td, embedding_provider=provider)
            user_id = "user-weight-test"
            being_id = "weight-tester"

            # Save notes with both user_id and being_id
            note_a = store.append_working_note(
                user_id=user_id, session_id="s1",
                title="Note A", content="Note A content",
                being_id=being_id,
            )
            note_b = store.append_working_note(
                user_id=user_id, session_id="s1",
                title="Note B", content="Note B content",
                being_id=being_id,
            )

            # Recall by user_id
            user_results = store._recall_markdown(user_id, "search query", limit=10)
            # Recall by being_id
            being_results = store._recall_markdown_by_being(being_id, "search query", limit=10)

            # Both should return same notes in same order with same scores
            assert len(user_results) == len(being_results) == 2

            user_scores = {r["note_id"]: r["score"] for r in user_results}
            being_scores = {r["note_id"]: r["score"] for r in being_results}

            for nid in user_scores:
                assert abs(user_scores[nid] - being_scores[nid]) < 1e-9, (
                    f"Score mismatch for {nid}: user={user_scores[nid]}, being={being_scores[nid]}"
                )

            # Same ranking order
            assert [r["note_id"] for r in user_results] == [r["note_id"] for r in being_results]
