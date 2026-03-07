"""Tests for embedding-based similarity scoring in being-scoped memory recall.

Verifies that _recall_markdown_by_being() uses embedding scores when an
embedding provider is available, matching the behavior of _recall_markdown().
"""
from __future__ import annotations

import json
import math
import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

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
