"""PostgreSQL backend with the same interface as RuntimeDB (SQLite)."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Mapping

import psycopg
from psycopg.rows import dict_row


class _PgCursor:
    """Thin wrapper around psycopg cursor to match sqlite3.Cursor interface.

    Exposes .fetchone(), .fetchall(), .rowcount, and dict-like row access.
    """

    def __init__(self, cursor: psycopg.Cursor):
        self._cur = cursor

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def lastrowid(self) -> int | None:
        return None  # Postgres doesn't expose lastrowid the same way

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)


class PostgresDB:
    """PostgreSQL connection wrapper matching the RuntimeDB interface.

    Uses psycopg v3 with dict_row factory so rows are dict-like,
    matching sqlite3.Row behavior.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = psycopg.connect(dsn, autocommit=False, row_factory=dict_row)
        self._lock = threading.RLock()

    @property
    def conn(self):
        return self._conn

    def _convert_sql(self, sql: str) -> str:
        """Convert SQLite ? placeholders to Postgres %s."""
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> _PgCursor:
        converted = self._convert_sql(sql)
        # Skip SQLite-specific PRAGMA statements
        if converted.strip().upper().startswith("PRAGMA"):
            return _PgCursor(self._conn.cursor())
        with self._lock:
            cur = self._conn.execute(converted, params)
            return _PgCursor(cur)

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> _PgCursor:
        converted = self._convert_sql(sql)
        with self._lock:
            cur = self._conn.cursor()
            cur.executemany(converted, list(seq_of_params))
            return _PgCursor(cur)

    def execute_commit(self, sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> _PgCursor:
        """Execute a statement and commit atomically."""
        converted = self._convert_sql(sql)
        if converted.strip().upper().startswith("PRAGMA"):
            return _PgCursor(self._conn.cursor())
        with self._lock:
            cur = self._conn.execute(converted, params)
            self._conn.commit()
            return _PgCursor(cur)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Context manager for multi-statement transactions."""
        with self._lock:
            try:
                yield self
                self._conn.commit()
            except BaseException:
                self._conn.rollback()
                raise

    def script(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script.

        Filters out SQLite-specific PRAGMA statements and converts
        AUTOINCREMENT to Postgres SERIAL.
        """
        with self._lock:
            statements = []
            for stmt in sql_script.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                # Skip PRAGMAs
                if stmt.upper().startswith("PRAGMA"):
                    continue
                # Convert SQLite AUTOINCREMENT to Postgres SERIAL
                stmt = stmt.replace(
                    "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "SERIAL PRIMARY KEY",
                )
                statements.append(stmt)
            for stmt in statements:
                self._conn.execute(stmt)
            self._conn.commit()

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
