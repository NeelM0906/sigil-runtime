from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bomba_sr.storage.db import RuntimeDB


META_MEMORY_PATTERNS = [
    re.compile(r"\bdo you remember\b", re.IGNORECASE),
    re.compile(r"\bcan you recall\b", re.IGNORECASE),
    re.compile(r"\bi don't (have|remember|recall)\b", re.IGNORECASE),
    re.compile(r"\bdid i tell you\b", re.IGNORECASE),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MemoryCandidate:
    user_id: str
    key: str
    content: str
    tier: str = "semantic"
    entities: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    recency_ts: str | None = None


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
            """
        )
        self.db.commit()

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
                  recency_ts, active, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
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
            "INSERT INTO memory_archive (id, memory_id, user_id, memory_key, old_content, archived_at, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                existing_id,
                candidate.user_id,
                candidate.key,
                existing_content,
                now,
                "contradiction_or_update",
            ),
        )
        self.db.execute("UPDATE memories SET active = 0, updated_at = ? WHERE id = ?", (now, existing_id))

        new_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO memories (
              id, user_id, memory_key, tier, content, entities, evidence_refs,
              recency_ts, active, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
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
            ),
        )
        self.db.commit()
        return new_id

    def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        recency_half_life_days: float = 14.0,
        recency_weight: float = 0.15,
    ) -> list[RetrievedMemory]:
        rows = self.db.execute(
            "SELECT * FROM memories WHERE user_id = ? AND active = 1 AND tier = 'semantic'",
            (user_id,),
        ).fetchall()

        scored: list[RetrievedMemory] = []
        for row in rows:
            content = str(row["content"])
            if self._is_meta_noise(content):
                continue

            lexical = self._lexical_score(query, content)
            recency_boost = self._recency_boost(
                recency_ts=str(row["recency_ts"]),
                half_life_days=recency_half_life_days,
                weight=recency_weight,
            )
            score = lexical + recency_boost
            scored.append(
                RetrievedMemory(
                    memory_id=str(row["id"]),
                    key=str(row["memory_key"]),
                    content=content,
                    score=score,
                    recency_boost=recency_boost,
                    lexical_score=lexical,
                    recency_ts=str(row["recency_ts"]),
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def archive_count(self, user_id: str, key: str) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) AS c FROM memory_archive WHERE user_id = ? AND memory_key = ?",
            (user_id, key),
        ).fetchone()
        return int(row["c"]) if row is not None else 0

    @staticmethod
    def _is_meta_noise(text: str) -> bool:
        t = text.strip()
        return any(pattern.search(t) for pattern in META_MEMORY_PATTERNS)

    @staticmethod
    def _lexical_score(query: str, content: str) -> float:
        q_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) >= 2}
        c_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", content.lower()) if len(t) >= 2}
        if not q_terms or not c_terms:
            return 0.0
        overlap = len(q_terms & c_terms)
        return overlap / len(q_terms)

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
