"""Shared MC database factory — PostgreSQL or SQLite."""
from __future__ import annotations

import os
from pathlib import Path


def create_shared_db():
    """Create the shared Mission Control database connection.

    If BOMBA_POSTGRES_DSN is set, use PostgreSQL.
    Otherwise fall back to SQLite at BOMBA_RUNTIME_HOME/bomba_runtime.db.
    """
    dsn = os.getenv("BOMBA_POSTGRES_DSN")
    if dsn:
        from bomba_sr.storage.postgres import PostgresDB
        return PostgresDB(dsn)

    from bomba_sr.storage.db import RuntimeDB
    runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
    runtime_home.mkdir(parents=True, exist_ok=True)
    return RuntimeDB(runtime_home / "bomba_runtime.db")
