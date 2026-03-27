"""Callagy Recovery PAD Database — read-only query tool.

Connects to the MariaDB PAD system (callagy_cms) and allows beings
to run SELECT queries. Writing is blocked at the tool level.

Only available to Recovery team tenants.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

log = logging.getLogger(__name__)

_BLOCKED_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"}


def _get_connection():
    """Get a MariaDB connection using env vars."""
    import pymysql
    return pymysql.connect(
        host=os.environ.get("CALLAGY_PAD_HOST", "60.60.60.201"),
        port=int(os.environ.get("CALLAGY_PAD_PORT", "3306")),
        user=os.environ.get("CALLAGY_PAD_USER", ""),
        password=os.environ.get("CALLAGY_PAD_PASSWORD", ""),
        database=os.environ.get("CALLAGY_PAD_DATABASE", "callagy_cms"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
    )


def _pad_query(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Execute a read-only SQL query against the Callagy PAD database."""
    query = str(arguments.get("query") or "").strip()
    limit = int(arguments.get("limit") or 100)

    if not query:
        raise ValueError("query is required")

    # Block write operations
    first_word = query.split()[0].lower() if query.split() else ""
    if first_word in _BLOCKED_KEYWORDS:
        raise ValueError(f"Write operations are not allowed. Only SELECT queries permitted.")
    for kw in _BLOCKED_KEYWORDS:
        if f" {kw} " in f" {query.lower()} ":
            raise ValueError(f"Query contains blocked keyword '{kw}'. Only SELECT queries permitted.")

    # Force LIMIT if not present
    if "limit" not in query.lower():
        query = f"{query} LIMIT {limit}"

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        return {
            "rows": rows[:limit],
            "row_count": len(rows),
            "columns": column_names,
            "query": query,
            "truncated": len(rows) > limit,
        }
    except Exception as exc:
        return {"error": str(exc), "query": query}


def _pad_tables(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """List tables in the PAD database with row counts."""
    search = str(arguments.get("search") or "").strip().lower()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cursor.fetchall()]

        if search:
            tables = [t for t in tables if search in t.lower()]

        result = []
        for t in tables[:50]:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{t}`")
                cnt = cursor.fetchone()["cnt"]
                result.append({"table": t, "rows": cnt})
            except Exception:
                result.append({"table": t, "rows": -1})

        conn.close()
        return {"tables": result, "total": len(tables), "shown": len(result)}
    except Exception as exc:
        return {"error": str(exc)}


def _pad_describe(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Describe a table's columns and types."""
    table = str(arguments.get("table") or "").strip()
    if not table:
        raise ValueError("table name is required")

    # Sanitize table name
    if not all(c.isalnum() or c == "_" for c in table):
        raise ValueError("Invalid table name")

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE `{table}`")
        columns = cursor.fetchall()

        # Also get sample row
        cursor.execute(f"SELECT * FROM `{table}` LIMIT 3")
        sample = cursor.fetchall()

        conn.close()
        return {
            "table": table,
            "columns": columns,
            "sample_rows": sample,
        }
    except Exception as exc:
        return {"error": str(exc)}


def builtin_pad_tools() -> list[ToolDefinition]:
    # Only register if PAD credentials are configured
    if not os.environ.get("CALLAGY_PAD_USER"):
        return []

    return [
        ToolDefinition(
            name="pad_query",
            description=(
                "Run a read-only SQL query against the Callagy Recovery PAD database (MariaDB). "
                "Contains PIP files, WC files, patients, treatments, settlements, documents, "
                "CPT codes, providers, and case management data. SELECT only — no writes."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max rows to return (default 100)",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_pad_query,
        ),
        ToolDefinition(
            name="pad_tables",
            description="List tables in the PAD database. Optionally filter by name.",
            parameters={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Filter tables by name (e.g., 'pip', 'wc', 'settlement')",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_pad_tables,
        ),
        ToolDefinition(
            name="pad_describe",
            description="Describe a PAD table's columns, types, and show sample rows.",
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name to describe (e.g., 'pip_files', 'wc_files')",
                    },
                },
                "required": ["table"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_pad_describe,
        ),
    ]
