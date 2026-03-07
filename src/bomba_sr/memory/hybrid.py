from __future__ import annotations

import json
import logging
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from bomba_sr.memory.consolidation import MemoryCandidate, MemoryConsolidator
from bomba_sr.memory.embeddings import EmbeddingProvider
from bomba_sr.storage.db import RuntimeDB

if TYPE_CHECKING:
    from bomba_sr.llm.providers import LLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Being resolution: derive being_id from session patterns
# ---------------------------------------------------------------------------

_BEING_PATTERNS = [
    # mc-chat-{being_id}  — direct chat
    (re.compile(r"^mc-chat-(.+)$"), 1),
    # subtask:{task_id}:{being_id}  — orchestration subtask
    (re.compile(r"^subtask:[^:]+:(.+)$"), 1),
]


def resolve_being_id(session_id: str | None, user_id: str | None = None) -> str | None:
    """Derive being_id from session_id patterns, or from user_id 'prime->X' pattern."""
    if session_id:
        for pattern, group in _BEING_PATTERNS:
            m = pattern.match(session_id)
            if m:
                return m.group(group)
    if user_id:
        if user_id.startswith("prime->"):
            return user_id[len("prime->"):]
    return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned[:80] or "note"


@dataclass(frozen=True)
class LearningDecision:
    update_id: str
    status: str
    confidence: float
    memory_id: str | None


class HybridMemoryStore:
    def __init__(
        self,
        db: RuntimeDB,
        memory_root: str | Path,
        auto_apply_confidence: float = 0.4,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        if not (0.0 <= auto_apply_confidence <= 1.0):
            raise ValueError("auto_apply_confidence must be in [0,1]")
        self.db = db
        self.memory_root = Path(memory_root).resolve()
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.auto_apply_confidence = auto_apply_confidence
        self.embedding_provider = embedding_provider
        self.consolidator = MemoryConsolidator(db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS markdown_notes (
              note_id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              session_id TEXT,
              relative_path TEXT NOT NULL,
              title TEXT NOT NULL,
              tags TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_markdown_notes_user_created
              ON markdown_notes(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS memory_embeddings (
              id TEXT PRIMARY KEY,
              note_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              model TEXT NOT NULL,
              vector_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(note_id) REFERENCES markdown_notes(note_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_memory_embeddings_user
              ON memory_embeddings(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS learning_updates (
              update_id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              memory_key TEXT NOT NULL,
              content TEXT NOT NULL,
              confidence REAL NOT NULL,
              status TEXT NOT NULL,
              evidence_refs TEXT NOT NULL,
              memory_id TEXT,
              reason TEXT,
              created_at TEXT NOT NULL,
              decided_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_learning_updates_user
              ON learning_updates(tenant_id, user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS conversation_turns (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              turn_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              user_message TEXT NOT NULL,
              assistant_message TEXT NOT NULL,
              turn_number INTEGER NOT NULL,
              token_estimate INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conv_turns_session
              ON conversation_turns(tenant_id, session_id, turn_number DESC);

            CREATE TABLE IF NOT EXISTS session_summaries (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              summary_text TEXT NOT NULL,
              covers_through_turn INTEGER NOT NULL,
              token_estimate INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_session_summaries
              ON session_summaries(tenant_id, session_id, covers_through_turn DESC);
            """
        )
        self.db.commit()
        # Add being_id column to markdown_notes (migration)
        self._ensure_column("markdown_notes", "being_id", "TEXT")

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        rows = self.db.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column in existing:
            return
        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        self.db.commit()

    def append_working_note(
        self,
        user_id: str,
        session_id: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        being_id: str | None = None,
    ) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("content cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")

        now = datetime.now(timezone.utc)
        rel_dir = Path(user_id) / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        abs_dir = self.memory_root / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)

        note_id = str(uuid.uuid4())
        name = f"{now.strftime('%H%M%S')}-{slugify(title)}-{note_id[:8]}.md"
        rel_path = rel_dir / name
        abs_path = self.memory_root / rel_path

        front_matter = {
            "note_id": note_id,
            "user_id": user_id,
            "session_id": session_id,
            "title": title,
            "tags": tags or [],
            "confidence": confidence,
            "created_at": now.isoformat(),
        }
        payload = [
            "---",
            json.dumps(front_matter, ensure_ascii=True),
            "---",
            "",
            content.strip(),
            "",
        ]
        abs_path.write_text("\n".join(payload), encoding="utf-8")

        self.db.execute(
            """
            INSERT INTO markdown_notes (
              note_id, user_id, session_id, relative_path, title, tags, confidence, created_at, being_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                user_id,
                session_id,
                str(rel_path),
                title,
                json.dumps(tags or []),
                confidence,
                now.isoformat(),
                being_id,
            ),
        )

        if self.embedding_provider is not None:
            vectors = self.embedding_provider.embed([content])
            if vectors:
                self.db.execute(
                    """
                    INSERT INTO memory_embeddings (id, note_id, user_id, model, vector_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        note_id,
                        user_id,
                        self.embedding_provider.model,
                        json.dumps(vectors[0], separators=(",", ":")),
                        now.isoformat(),
                    ),
                )

        self.db.commit()
        return {
            "note_id": note_id,
            "path": str(abs_path),
            "relative_path": str(rel_path),
            "title": title,
            "created_at": now.isoformat(),
            "confidence": confidence,
        }

    def learn_semantic(
        self,
        tenant_id: str,
        user_id: str,
        memory_key: str,
        content: str,
        confidence: float,
        evidence_refs: list[str] | None = None,
        reason: str | None = None,
        being_id: str | None = None,
    ) -> LearningDecision:
        if not content.strip():
            raise ValueError("content cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")

        now = utc_now_iso()
        update_id = str(uuid.uuid4())
        status = "pending"
        memory_id: str | None = None

        if confidence >= self.auto_apply_confidence:
            status = "applied"
            memory_id = self.consolidator.upsert(
                MemoryCandidate(
                    user_id=user_id,
                    key=memory_key,
                    content=content,
                    evidence_refs=tuple(evidence_refs or ()),
                    recency_ts=now,
                    being_id=being_id,
                )
            )

        self.db.execute(
            """
            INSERT INTO learning_updates (
              update_id, tenant_id, user_id, memory_key, content, confidence,
              status, evidence_refs, memory_id, reason, created_at, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update_id,
                tenant_id,
                user_id,
                memory_key,
                content,
                confidence,
                status,
                json.dumps(evidence_refs or []),
                memory_id,
                reason,
                now,
                now if status == "applied" else None,
            ),
        )
        self.db.commit()
        return LearningDecision(update_id=update_id, status=status, confidence=confidence, memory_id=memory_id)

    def approve_learning(self, update_id: str, approved: bool) -> LearningDecision:
        row = self.db.execute(
            "SELECT * FROM learning_updates WHERE update_id = ?",
            (update_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"learning update not found: {update_id}")

        status = str(row["status"])
        if status in {"applied", "rejected"}:
            return LearningDecision(
                update_id=update_id,
                status=status,
                confidence=float(row["confidence"]),
                memory_id=(str(row["memory_id"]) if row["memory_id"] else None),
            )

        decided_at = utc_now_iso()
        memory_id: str | None = None
        next_status = "rejected"

        if approved:
            evidence_refs = json.loads(str(row["evidence_refs"]))
            memory_id = self.consolidator.upsert(
                MemoryCandidate(
                    user_id=str(row["user_id"]),
                    key=str(row["memory_key"]),
                    content=str(row["content"]),
                    evidence_refs=tuple(str(x) for x in evidence_refs),
                    recency_ts=decided_at,
                )
            )
            next_status = "applied"

        self.db.execute(
            """
            UPDATE learning_updates
            SET status = ?, memory_id = ?, decided_at = ?
            WHERE update_id = ?
            """,
            (next_status, memory_id, decided_at, update_id),
        )
        self.db.commit()
        return LearningDecision(
            update_id=update_id,
            status=next_status,
            confidence=float(row["confidence"]),
            memory_id=memory_id,
        )

    def pending_approvals(self, tenant_id: str, user_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT update_id, memory_key, content, confidence, reason, created_at
            FROM learning_updates
            WHERE tenant_id = ? AND user_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            """,
            (tenant_id, user_id),
        ).fetchall()
        return [
            {
                "update_id": str(r["update_id"]),
                "memory_key": str(r["memory_key"]),
                "content": str(r["content"]),
                "confidence": float(r["confidence"]),
                "reason": str(r["reason"]) if r["reason"] is not None else None,
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]

    def learn_procedural(
        self,
        user_id: str,
        strategy_key: str,
        content: str,
        success: bool,
        being_id: str | None = None,
    ) -> str:
        return self.consolidator.learn_procedural(
            user_id=user_id,
            strategy_key=strategy_key,
            content=content,
            success=success,
            being_id=being_id,
        )

    def recall_procedural(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.consolidator.recall_procedural(user_id=user_id, query=query, limit=limit)

    def recall(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        semantic = self.consolidator.retrieve(user_id=user_id, query=query, limit=max(1, limit // 2))
        markdown = self._recall_markdown(user_id=user_id, query=query, limit=max(1, limit - len(semantic)))

        return {
            "semantic": [
                {
                    "memory_id": m.memory_id,
                    "key": m.key,
                    "content": m.content,
                    "score": m.score,
                    "recency_boost": m.recency_boost,
                    "recency_ts": m.recency_ts,
                    "source": f"memory://semantic/{m.memory_id}",
                }
                for m in semantic
            ],
            "markdown": markdown,
        }

    def recall_by_being(
        self,
        being_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Recall memories scoped by being_id (cross-context access)."""
        semantic = self.consolidator.retrieve_by_being(being_id=being_id, query=query, limit=max(1, limit // 2))
        markdown = self._recall_markdown_by_being(being_id=being_id, query=query, limit=max(1, limit - len(semantic)))

        return {
            "semantic": [
                {
                    "memory_id": m.memory_id,
                    "key": m.key,
                    "content": m.content,
                    "score": m.score,
                    "recency_boost": m.recency_boost,
                    "recency_ts": m.recency_ts,
                    "source": f"memory://semantic/{m.memory_id}",
                }
                for m in semantic
            ],
            "markdown": markdown,
        }

    def recall_procedural_by_being(self, being_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall procedural memories scoped by being_id."""
        return self.consolidator.recall_procedural_by_being(being_id=being_id, query=query, limit=limit)

    def _recall_markdown(self, user_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT note_id, relative_path, title, confidence, created_at
            FROM markdown_notes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 300
            """,
            (user_id,),
        ).fetchall()

        if not rows:
            return []

        scores: dict[str, float] = {}
        embedding_scores = self._embedding_scores(user_id=user_id, query=query)
        for note_id, score in embedding_scores.items():
            scores[note_id] = score

        for row in rows:
            note_id = str(row["note_id"])
            if note_id in scores:
                continue
            text = self._read_note_body(str(row["relative_path"]))
            scores[note_id] = self._lexical_score(query, text)

        ranked = sorted(rows, key=lambda r: scores.get(str(r["note_id"]), 0.0), reverse=True)
        out: list[dict[str, Any]] = []
        for row in ranked[:limit]:
            note_id = str(row["note_id"])
            rel_path = str(row["relative_path"])
            body = self._read_note_body(rel_path)
            out.append(
                {
                    "note_id": note_id,
                    "title": str(row["title"]),
                    "path": str((self.memory_root / rel_path).resolve()),
                    "score": float(scores.get(note_id, 0.0)),
                    "confidence": float(row["confidence"]),
                    "created_at": str(row["created_at"]),
                    "snippet": body[:280],
                    "source": f"memory://markdown/{note_id}",
                }
            )
        return out

    def _recall_markdown_by_being(self, being_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        """Recall markdown notes scoped by being_id."""
        rows = self.db.execute(
            """
            SELECT note_id, relative_path, title, confidence, created_at
            FROM markdown_notes
            WHERE being_id = ?
            ORDER BY created_at DESC
            LIMIT 300
            """,
            (being_id,),
        ).fetchall()

        if not rows:
            return []

        scores: dict[str, float] = {}
        embedding_scores = self._embedding_scores_by_being(being_id=being_id, query=query)
        for note_id, score in embedding_scores.items():
            scores[note_id] = score

        for row in rows:
            note_id = str(row["note_id"])
            if note_id in scores:
                continue
            text = self._read_note_body(str(row["relative_path"]))
            scores[note_id] = self._lexical_score(query, text)

        ranked = sorted(rows, key=lambda r: scores.get(str(r["note_id"]), 0.0), reverse=True)
        out: list[dict[str, Any]] = []
        for row in ranked[:limit]:
            note_id = str(row["note_id"])
            rel_path = str(row["relative_path"])
            body = self._read_note_body(rel_path)
            out.append(
                {
                    "note_id": note_id,
                    "title": str(row["title"]),
                    "path": str((self.memory_root / rel_path).resolve()),
                    "score": float(scores.get(note_id, 0.0)),
                    "confidence": float(row["confidence"]),
                    "created_at": str(row["created_at"]),
                    "snippet": body[:280],
                    "source": f"memory://markdown/{note_id}",
                }
            )
        return out

    def _embedding_scores(self, user_id: str, query: str) -> dict[str, float]:
        if self.embedding_provider is None:
            return {}
        rows = self.db.execute(
            "SELECT note_id, vector_json FROM memory_embeddings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        if not rows:
            return {}

        query_vectors = self.embedding_provider.embed([query])
        if not query_vectors:
            return {}
        query_vec = query_vectors[0]

        scores: dict[str, float] = {}
        for row in rows:
            note_id = str(row["note_id"])
            vec = json.loads(str(row["vector_json"]))
            scores[note_id] = self._cosine(query_vec, [float(x) for x in vec])
        return scores

    def _embedding_scores_by_being(self, being_id: str, query: str) -> dict[str, float]:
        """Compute embedding similarity scores for notes owned by a being."""
        if self.embedding_provider is None:
            return {}
        rows = self.db.execute(
            """
            SELECT e.note_id, e.vector_json
            FROM memory_embeddings e
            JOIN markdown_notes n ON n.note_id = e.note_id
            WHERE n.being_id = ?
            ORDER BY n.created_at DESC
            LIMIT 300
            """,
            (being_id,),
        ).fetchall()
        if not rows:
            return {}

        query_vectors = self.embedding_provider.embed([query])
        if not query_vectors:
            return {}
        query_vec = query_vectors[0]

        scores: dict[str, float] = {}
        for row in rows:
            note_id = str(row["note_id"])
            vec = json.loads(str(row["vector_json"]))
            scores[note_id] = self._cosine(query_vec, [float(x) for x in vec])
        return scores

    def record_turn(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> int:
        latest = self.db.execute(
            """
            SELECT COALESCE(MAX(turn_number), 0) AS max_turn
            FROM conversation_turns
            WHERE tenant_id = ? AND session_id = ?
            """,
            (tenant_id, session_id),
        ).fetchone()
        next_turn = int(latest["max_turn"]) + 1 if latest is not None else 1
        token_estimate = max(1, int((len(user_message) + len(assistant_message)) / 4))
        now = utc_now_iso()
        self.db.execute(
            """
            INSERT INTO conversation_turns (
              id, tenant_id, session_id, turn_id, user_id, user_message, assistant_message,
              turn_number, token_estimate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                session_id,
                turn_id,
                user_id,
                user_message,
                assistant_message,
                next_turn,
                token_estimate,
                now,
            ),
        )
        self.db.commit()
        return next_turn

    def get_recent_turn_records(self, tenant_id: str, session_id: str, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT turn_number, turn_id, user_message, assistant_message, created_at
            FROM conversation_turns
            WHERE tenant_id = ? AND session_id = ?
            ORDER BY turn_number DESC
            LIMIT ?
            """,
            (tenant_id, session_id, max(1, limit)),
        ).fetchall()
        ordered = list(reversed(rows))
        return [
            {
                "turn_number": int(row["turn_number"]),
                "turn_id": str(row["turn_id"]),
                "user_message": str(row["user_message"]),
                "assistant_message": str(row["assistant_message"]),
                "created_at": str(row["created_at"]),
            }
            for row in ordered
        ]

    def get_recent_turns(self, tenant_id: str, session_id: str, limit: int = 5) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for row in self.get_recent_turn_records(tenant_id=tenant_id, session_id=session_id, limit=limit):
            out.append({"role": "user", "content": row["user_message"]})
            out.append({"role": "assistant", "content": row["assistant_message"]})
        return out

    def get_turns_for_summary(
        self,
        tenant_id: str,
        session_id: str,
        covers_through_turn: int,
        recent_window: int = 5,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        latest = self.db.execute(
            """
            SELECT COALESCE(MAX(turn_number), 0) AS max_turn
            FROM conversation_turns
            WHERE tenant_id = ? AND session_id = ?
            """,
            (tenant_id, session_id),
        ).fetchone()
        max_turn = int(latest["max_turn"]) if latest is not None else 0
        summary_cutoff = max(0, max_turn - max(1, recent_window))
        if summary_cutoff <= covers_through_turn:
            return []

        rows = self.db.execute(
            """
            SELECT turn_number, user_message, assistant_message
            FROM conversation_turns
            WHERE tenant_id = ? AND session_id = ?
              AND turn_number > ? AND turn_number <= ?
            ORDER BY turn_number ASC
            LIMIT ?
            """,
            (
                tenant_id,
                session_id,
                int(covers_through_turn),
                summary_cutoff,
                max(1, limit),
            ),
        ).fetchall()
        return [
            {
                "turn_number": int(row["turn_number"]),
                "user_message": str(row["user_message"]),
                "assistant_message": str(row["assistant_message"]),
            }
            for row in rows
        ]

    def get_session_summary(self, tenant_id: str, session_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            """
            SELECT summary_text, covers_through_turn, token_estimate, created_at, updated_at
            FROM session_summaries
            WHERE tenant_id = ? AND session_id = ?
            ORDER BY covers_through_turn DESC
            LIMIT 1
            """,
            (tenant_id, session_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "summary_text": str(row["summary_text"]),
            "covers_through_turn": int(row["covers_through_turn"]),
            "token_estimate": int(row["token_estimate"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def update_session_summary(
        self,
        tenant_id: str,
        session_id: str,
        user_id: str,
        summary_text: str,
        covers_through_turn: int,
    ) -> dict[str, Any]:
        normalized = summary_text.strip()
        if not normalized:
            raise ValueError("summary_text cannot be empty")
        now = utc_now_iso()
        token_estimate = max(1, int(len(normalized) / 4))
        self.db.execute(
            """
            INSERT INTO session_summaries (
              id, tenant_id, session_id, user_id, summary_text, covers_through_turn,
              token_estimate, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, session_id) DO UPDATE SET
              summary_text = excluded.summary_text,
              covers_through_turn = excluded.covers_through_turn,
              token_estimate = excluded.token_estimate,
              updated_at = excluded.updated_at
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                session_id,
                user_id,
                normalized,
                int(covers_through_turn),
                token_estimate,
                now,
                now,
            ),
        )
        self.db.commit()
        return {
            "summary_text": normalized,
            "covers_through_turn": int(covers_through_turn),
            "token_estimate": token_estimate,
            "updated_at": now,
        }

    def generate_session_summary(
        self,
        turns: list[dict[str, Any]],
        provider: "LLMProvider",
        model_id: str,
        existing_summary: str | None = None,
    ) -> str:
        if not turns:
            return ""
        from bomba_sr.llm.providers import ChatMessage

        transcript_lines: list[str] = []
        for row in turns:
            transcript_lines.append(f"Turn {row['turn_number']} user: {row['user_message']}")
            transcript_lines.append(f"Turn {row['turn_number']} assistant: {row['assistant_message']}")
        transcript = "\n".join(transcript_lines)
        if len(transcript) > 24000:
            transcript = transcript[:24000]
        prior = existing_summary.strip() if isinstance(existing_summary, str) and existing_summary.strip() else "None"

        prompt = (
            "Summarize this conversation history into key facts, decisions, preferences, and pending tasks. "
            "Preserve durable user-specific details. Keep it concise.\n\n"
            f"Previous summary:\n{prior}\n\n"
            f"New turns:\n{transcript}"
        )
        try:
            response = provider.generate(
                model=model_id,
                messages=[
                    ChatMessage(
                        role="system",
                        content=(
                            "Produce a compact session summary with only durable context. "
                            "Max length: 200 tokens."
                        ),
                    ),
                    ChatMessage(role="user", content=prompt),
                ],
            )
            summary = (response.text or "").strip()
            if summary:
                return summary[:8000]
        except Exception as exc:
            logger.warning(
                "session summary LLM call failed; using fallback summary",
                exc_info=exc,
            )
        fallback = f"{prior}\n\n{transcript[:4000]}".strip()
        return fallback[:8000]

    def _read_note_body(self, relative_path: str) -> str:
        try:
            text = (self.memory_root / relative_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        except OSError:
            return ""
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
        return text.strip()

    @staticmethod
    def _lexical_score(query: str, content: str) -> float:
        q_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) >= 2}
        c_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", content.lower()) if len(t) >= 2}
        if not q_terms:
            return 0.0
        return len(q_terms & c_terms) / len(q_terms)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)
