from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Mapping, Any


class RuntimeDB:
    """Small SQLite helper for runtime services.

    The DB is file-backed by default for continuity across runs.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._lock = threading.RLock()
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executemany(sql, seq_of_params)

    def script(self, sql_script: str) -> None:
        with self._lock:
            self._conn.executescript(sql_script)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def dict_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
