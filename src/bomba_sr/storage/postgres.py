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
        self._conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        self._lock = threading.RLock()

    @property
    def conn(self):
        return self._conn

    def _convert_sql(self, sql: str) -> str:
        """Convert SQLite SQL to Postgres-compatible SQL."""
        import re
        converted = sql.replace("?", "%s")
        # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        converted = re.sub(
            r"INSERT\s+OR\s+IGNORE\s+INTO",
            "INSERT INTO",
            converted,
            flags=re.IGNORECASE,
        )
        if re.search(r"INSERT\s+INTO", converted, re.IGNORECASE) and "ON CONFLICT" not in converted.upper():
            # Only add ON CONFLICT DO NOTHING if the original had OR IGNORE
            if re.search(r"INSERT\s+OR\s+IGNORE", sql, re.IGNORECASE):
                converted = converted.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        # INSERT OR REPLACE → INSERT ... ON CONFLICT DO UPDATE (simplified)
        converted = re.sub(
            r"INSERT\s+OR\s+REPLACE\s+INTO",
            "INSERT INTO",
            converted,
            flags=re.IGNORECASE,
        )
        return converted

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
        """Execute a statement (auto-committed in autocommit mode)."""
        return self.execute(sql, params)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Context manager for multi-statement transactions.

        Temporarily disables autocommit for the transaction block.
        """
        with self._lock:
            self._conn.autocommit = False
            try:
                yield self
                self._conn.commit()
            except BaseException:
                self._conn.rollback()
                raise
            finally:
                self._conn.autocommit = True

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
            # In autocommit mode, each statement is already committed

    def commit(self) -> None:
        # No-op in autocommit mode; explicit commit only needed inside transaction()
        if not self._conn.autocommit:
            with self._lock:
                self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
