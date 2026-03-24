from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bomba_sr.memory.utils import ensure_column, lexical_score, utc_now_iso
from bomba_sr.storage.db import RuntimeDB


META_MEMORY_PATTERNS = [
    re.compile(r"\bdo you remember\b", re.IGNORECASE),
    re.compile(r"\bcan you recall\b", re.IGNORECASE),
    re.compile(r"\bi don't (have|remember|recall)\b", re.IGNORECASE),
    re.compile(r"\bdid i tell you\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class MemoryCandidate:
    user_id: str
    key: str
    content: str
    tier: str = "semantic"
    entities: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    recency_ts: str | None = None
    being_id: str | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class RetrievedMemory:
    memory_id: str
    key: str
    content: str
    score: float
    recency_boost: float
    lexical_score: float
    recency_ts: str


class MemoryConsolidator:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
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
              UNIQUE(user_id, strategy_key)
            );

            CREATE INDEX IF NOT EXISTS idx_procedural_memories_user
              ON procedural_memories(user_id, active, updated_at DESC);
            """
        )
        self.db.commit()
        # Add being_id and session_id columns to existing tables (migration)
        ensure_column(self.db, "memories", "being_id", "TEXT")
        ensure_column(self.db, "memories", "session_id", "TEXT")
        ensure_column(self.db, "procedural_memories", "being_id", "TEXT")
        ensure_column(self.db, "memory_archive", "being_id", "TEXT")

    def upsert(self, candidate: MemoryCandidate) -> str:
        now = utc_now_iso()
        recency_ts = candidate.recency_ts or now
        row = self.db.execute(
            """
            SELECT * FROM memories
            WHERE user_id = ? AND memory_key = ? AND active = 1
            ORDER BY version DESC LIMIT 1
            """,
            (candidate.user_id, candidate.key),
        ).fetchone()

        if row is None:
            memory_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO memories (
                  id, user_id, memory_key, tier, content, entities, evidence_refs,
                  recency_ts, active, version, created_at, updated_at, being_id, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    candidate.user_id,
                    candidate.key,
                    candidate.tier,
                    candidate.content,
                    json.dumps(list(candidate.entities)),
                    json.dumps(list(candidate.evidence_refs)),
                    recency_ts,
                    now,
                    now,
                    candidate.being_id,
                    candidate.session_id,
                ),
            )
            self.db.commit()
            return memory_id

        existing_content = str(row["content"])
        existing_id = str(row["id"])
        version = int(row["version"])

        if existing_content.strip() == candidate.content.strip():
            self.db.execute(
                """
                UPDATE memories
                SET evidence_refs = ?, recency_ts = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(list(candidate.evidence_refs)),
                    recency_ts,
                    now,
                    existing_id,
                ),
            )
            self.db.commit()
            return existing_id

        # Contradiction/update path: archive older belief and promote new one.
        self.db.execute(
            "INSERT INTO memory_archive (id, memory_id, user_id, memory_key, old_content, archived_at, reason, being_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                existing_id,
                candidate.user_id,
                candidate.key,
                existing_content,
                now,
                "contradiction_or_update",
                candidate.being_id or row["being_id"],
            ),
        )
        self.db.execute("UPDATE memories SET active = 0, updated_at = ? WHERE id = ?", (now, existing_id))

        new_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO memories (
              id, user_id, memory_key, tier, content, entities, evidence_refs,
              recency_ts, active, version, created_at, updated_at, being_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                new_id,
                candidate.user_id,
                candidate.key,
                candidate.tier,
                candidate.content,
                json.dumps(list(candidate.entities)),
                json.dumps(list(candidate.evidence_refs)),
                recency_ts,
                version + 1,
                now,
                now,
                candidate.being_id,
            ),
        )
        self.db.commit()
        return new_id

    def _retrieve_scored(
        self,
        scope_col: str,
        scope_val: str,
        query: str,
        limit: int = 10,
        recency_half_life_days: float = 14.0,
        recency_weight: float = 0.15,
        session_id: str | None = None,
    ) -> list[RetrievedMemory]:
        rows = self.db.execute(
            f"SELECT * FROM memories WHERE {scope_col} = ? AND active = 1 AND tier = 'semantic'",
            (scope_val,),
        ).fetchall()

        # Session boost: memories from the current session get a score bonus
        _SESSION_BOOST = 0.3

        scored: list[RetrievedMemory] = []
        for row in rows:
            content = str(row["content"])
            if self._is_meta_noise(content):
                continue

            lex = lexical_score(query, content)
            recency_boost = self._recency_boost(
                recency_ts=str(row["recency_ts"]),
                half_life_days=recency_half_life_days,
                weight=recency_weight,
            )
            score = lex + recency_boost

            # Boost memories from the current session
            row_session = None
            try:
                row_session = row["session_id"]
            except (IndexError, KeyError):
                pass
            if session_id and row_session == session_id:
                score += _SESSION_BOOST

            scored.append(
                RetrievedMemory(
                    memory_id=str(row["id"]),
                    key=str(row["memory_key"]),
                    content=content,
                    score=score,
                    recency_boost=recency_boost,
                    lexical_score=lex,
                    recency_ts=str(row["recency_ts"]),
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        recency_half_life_days: float = 14.0,
        recency_weight: float = 0.15,
        session_id: str | None = None,
    ) -> list[RetrievedMemory]:
        return self._retrieve_scored("user_id", user_id, query, limit, recency_half_life_days, recency_weight, session_id=session_id)

    def learn_procedural(
        self,
        user_id: str,
        strategy_key: str,
        content: str,
        success: bool,
        being_id: str | None = None,
    ) -> str:
        normalized_key = strategy_key.strip()
        normalized_content = content.strip()
        if not normalized_key:
            raise ValueError("strategy_key cannot be empty")
        if not normalized_content:
            raise ValueError("content cannot be empty")

        now = utc_now_iso()
        row = self.db.execute(
            """
            SELECT id, success_count, failure_count
            FROM procedural_memories
            WHERE user_id = ? AND strategy_key = ? AND active = 1
            LIMIT 1
            """,
            (user_id, normalized_key),
        ).fetchone()

        if row is None:
            memory_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO procedural_memories (
                  id, user_id, strategy_key, content, success_count, failure_count,
                  active, created_at, updated_at, being_id
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    memory_id,
                    user_id,
                    normalized_key,
                    normalized_content,
                    1 if success else 0,
                    0 if success else 1,
                    now,
                    now,
                    being_id,
                ),
            )
            self.db.commit()
            return memory_id

        memory_id = str(row["id"])
        success_count = int(row["success_count"]) + (1 if success else 0)
        failure_count = int(row["failure_count"]) + (0 if success else 1)
        self.db.execute(
            """
            UPDATE procedural_memories
            SET content = ?, success_count = ?, failure_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalized_content,
                success_count,
                failure_count,
                now,
                memory_id,
            ),
        )
        self.db.commit()
        return memory_id

    def _recall_procedural_scored(self, scope_col: str, scope_val: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.db.execute(
            f"""
            SELECT *
            FROM procedural_memories
            WHERE {scope_col} = ? AND active = 1
            ORDER BY updated_at DESC
            LIMIT 200
            """,
            (scope_val,),
        ).fetchall()
        scored: list[dict[str, Any]] = []
        for row in rows:
            content = str(row["content"])
            lex = lexical_score(query, content)
            success_count = int(row["success_count"])
            failure_count = int(row["failure_count"])
            total = success_count + failure_count
            success_ratio = (success_count + 1) / (total + 2)
            score = lex * success_ratio
            scored.append(
                {
                    "id": str(row["id"]),
                    "strategy_key": str(row["strategy_key"]),
                    "content": content,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_ratio": success_ratio,
                    "lexical_score": lex,
                    "score": score,
                    "updated_at": str(row["updated_at"]),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(1, int(limit))]

    def recall_procedural(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._recall_procedural_scored("user_id", user_id, query, limit)

    def retrieve_by_being(
        self,
        being_id: str,
        query: str,
        limit: int = 10,
        recency_half_life_days: float = 14.0,
        recency_weight: float = 0.15,
    ) -> list[RetrievedMemory]:
        """Retrieve semantic memories scoped by being_id (cross-context)."""
        return self._retrieve_scored("being_id", being_id, query, limit, recency_half_life_days, recency_weight)

    def recall_procedural_by_being(self, being_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall procedural memories scoped by being_id."""
        return self._recall_procedural_scored("being_id", being_id, query, limit)

    @staticmethod
    def _is_meta_noise(text: str) -> bool:
        t = text.strip()
        return any(pattern.search(t) for pattern in META_MEMORY_PATTERNS)

    @staticmethod
    def _recency_boost(recency_ts: str, half_life_days: float, weight: float) -> float:
        try:
            ts = datetime.fromisoformat(recency_ts)
        except ValueError:
            return 0.0
        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
        return math.exp(-age_days / half_life_days) * weight
