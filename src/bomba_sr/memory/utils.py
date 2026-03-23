"""Shared helpers for the memory subsystem (internal — not re-exported)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bomba_sr.storage.db import RuntimeDB


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def lexical_score(query: str, content: str) -> float:
    q_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) >= 2}
    c_terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", content.lower()) if len(t) >= 2}
    if not q_terms or not c_terms:
        return 0.0
    return len(q_terms & c_terms) / len(q_terms)


def ensure_column(db: RuntimeDB, table: str, column: str, definition: str) -> None:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row["name"]) for row in rows}
    if column in existing:
        return
    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    db.commit()
