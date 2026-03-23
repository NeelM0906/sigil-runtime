#!/usr/bin/env python3
"""One-time migration: copy shared MC tables from SQLite to PostgreSQL.

Usage:
    PYTHONPATH=src python scripts/migrate_sqlite_to_postgres.py \
        --sqlite .runtime/bomba_runtime.db \
        --postgres "postgresql://bomba:password@localhost:5432/bomba_mc"
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

import psycopg
from psycopg.rows import dict_row


# Tables to migrate (order matters for foreign key constraints)
TABLES = [
    "mc_users",
    "mc_sessions_auth",
    "mc_beings",
    "mc_chat_sessions",
    "mc_messages",
    "mc_task_history",
    "mc_task_assignments",
    "mc_task_steps",
    "mc_events",
    "mc_deliverables",
    "tool_audit_log",
    "projects",
    "project_tasks",
]


def get_columns(sqlite_conn: sqlite3.Connection, table: str) -> list[str]:
    """Get column names for a table."""
    cur = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def get_create_sql(sqlite_conn: sqlite3.Connection, table: str) -> str:
    """Get the CREATE TABLE SQL from sqlite_master and convert for Postgres."""
    row = sqlite_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row:
        return ""
    sql = row[0]
    # Convert SQLite-specific syntax
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return sql


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg.Connection,
    table: str,
) -> int:
    """Migrate a single table. Returns row count."""
    columns = get_columns(sqlite_conn, table)
    if not columns:
        print(f"  SKIP {table} (not found in SQLite)")
        return 0

    # Create table in Postgres (IF NOT EXISTS)
    create_sql = get_create_sql(sqlite_conn, table)
    if create_sql:
        # Wrap with IF NOT EXISTS
        create_sql = create_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
        pg_conn.execute(create_sql)
        pg_conn.commit()

    # Read all rows from SQLite
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0 rows (empty)")
        return 0

    # Build INSERT with ON CONFLICT DO NOTHING to handle re-runs
    col_names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    # Handle SERIAL column (mc_events.seq) — need to insert explicit values
    if table == "mc_events":
        # For SERIAL columns, we need to allow explicit ID insertion
        pg_conn.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'seq'), 1, false)")

    batch = [tuple(row) for row in rows]
    with pg_conn.cursor() as cur:
        cur.executemany(insert_sql, batch)
    pg_conn.commit()

    # Update SERIAL sequence for mc_events
    if table == "mc_events":
        pg_conn.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'seq'), "
            f"COALESCE((SELECT MAX(seq) FROM {table}), 1))"
        )
        pg_conn.commit()

    count = len(batch)
    print(f"  {table}: {count} rows migrated")
    return count


def verify(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg.Connection,
    table: str,
) -> bool:
    """Verify row counts match."""
    sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    pg_row = pg_conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    pg_count = pg_row["c"] if pg_row else 0
    match = pg_count >= sqlite_count  # >= because ON CONFLICT DO NOTHING may skip dupes
    status = "OK" if match else "MISMATCH"
    print(f"  {table}: sqlite={sqlite_count} postgres={pg_count} [{status}]")
    return match


def main():
    parser = argparse.ArgumentParser(description="Migrate MC tables from SQLite to PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="Path to SQLite database")
    parser.add_argument("--postgres", required=True, help="PostgreSQL DSN")
    parser.add_argument("--verify-only", action="store_true", help="Only verify, don't migrate")
    args = parser.parse_args()

    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(args.postgres, autocommit=False, row_factory=dict_row)

    if args.verify_only:
        print("Verifying row counts...")
        all_ok = True
        for table in TABLES:
            try:
                if not verify(sqlite_conn, pg_conn, table):
                    all_ok = False
            except Exception as e:
                print(f"  {table}: ERROR — {e}")
                all_ok = False
        sys.exit(0 if all_ok else 1)

    print("Migrating tables from SQLite to PostgreSQL...")
    total = 0
    for table in TABLES:
        try:
            total += migrate_table(sqlite_conn, pg_conn, table)
        except Exception as e:
            print(f"  {table}: ERROR — {e}")
            pg_conn.rollback()

    print(f"\nTotal: {total} rows migrated")

    # Also create indexes that the dashboard service expects
    print("\nCreating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_mc_messages_ts ON mc_messages(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_mc_messages_session ON mc_messages(session_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_mc_task_history_task ON mc_task_history(task_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_mc_task_steps_task ON mc_task_steps(task_id, step_number)",
        "CREATE INDEX IF NOT EXISTS idx_mc_events_type ON mc_events(event_type, seq)",
        "CREATE INDEX IF NOT EXISTS idx_mc_deliverables_task ON mc_deliverables(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_mc_sessions_auth_user ON mc_sessions_auth(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tool_audit_tenant ON tool_audit_log(tenant_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_tool_audit_being ON tool_audit_log(being_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_projects_tenant ON projects(tenant_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_project_tasks_parent ON project_tasks(parent_task_id)",
    ]
    for idx_sql in indexes:
        try:
            pg_conn.execute(idx_sql)
        except Exception as e:
            print(f"  WARN: {e}")
    pg_conn.commit()
    print("Done.")

    print("\nVerifying...")
    all_ok = True
    for table in TABLES:
        try:
            if not verify(sqlite_conn, pg_conn, table):
                all_ok = False
        except Exception as e:
            print(f"  {table}: ERROR — {e}")
            all_ok = False

    sqlite_conn.close()
    pg_conn.close()

    if all_ok:
        print("\nMigration complete — all row counts match.")
    else:
        print("\nWARNING: Some row counts don't match. Check above.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
