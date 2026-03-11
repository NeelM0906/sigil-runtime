from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_READ_ONLY_SQL_RE = re.compile(r"^\s*(select|with|show|explain)\b", re.IGNORECASE)
_INFO_SCHEMA_TABLES_RE = re.compile(
    r"^\s*select\s+table_schema\s*,\s*table_name\s+from\s+information_schema\.tables\b.*?(?:limit\s+(?P<limit>\d+))?\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)
_SIMPLE_SELECT_RE = re.compile(
    r"^\s*select\s+(?P<select>[\w\*,\s\"]+)\s+from\s+(?P<table>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+where\s+(?P<where>.+?))?(?:\s+limit\s+(?P<limit>\d+))?\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _require_identifier(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    if not _IDENTIFIER_RE.fullmatch(cleaned):
        raise ValueError(f"{field_name} contains invalid characters")
    return cleaned


def _supabase_headers() -> tuple[str, dict[str, str]]:
    base_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    api_key = (
        os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not base_url or not api_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required for Supabase tools")
    headers = {
        "Accept": "application/json",
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "sigil-runtime/1.0",
    }
    return base_url, headers


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    body = None
    request_headers = dict(headers)
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except OSError:
            pass
        raise ValueError(f"HTTP {exc.code} from data service: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Data service request failed: {exc.reason}") from exc
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Data service returned invalid JSON") from exc


def _supabase_query(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    base_url, headers = _supabase_headers()
    table = _require_identifier(str(arguments.get("table") or ""), "table")
    select = str(arguments.get("select") or "*").strip() or "*"
    limit = max(1, min(500, int(arguments.get("limit") or 50)))
    filters = arguments.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object of column -> value")

    params: list[tuple[str, str]] = [("select", select), ("limit", str(limit))]
    for key, value in filters.items():
        column = _require_identifier(str(key), "filter column")
        params.append((column, f"eq.{value}"))

    query = urllib.parse.urlencode(params)
    url = f"{base_url}/rest/v1/{table}?{query}"
    rows = _http_json("GET", url, headers=headers)
    if not isinstance(rows, list):
        raise ValueError("Supabase query did not return a row array")
    return {"table": table, "count": len(rows), "rows": rows}


def _supabase_rpc(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    base_url, headers = _supabase_headers()
    function_name = _require_identifier(str(arguments.get("function") or ""), "function")
    params = arguments.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    url = f"{base_url}/rest/v1/rpc/{function_name}"
    result = _http_json("POST", url, headers=headers, payload=params)
    return {"function": function_name, "result": result}


def _postgres_query(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    try:
        import pg8000.native
    except Exception as exc:
        raise ValueError("pg8000 is required for postgres_query; install runtime dependencies first") from exc

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required for postgres_query")

    sql = str(arguments.get("sql") or "").strip()
    if not sql:
        raise ValueError("sql is required")
    if not _READ_ONLY_SQL_RE.match(sql):
        raise ValueError("postgres_query only permits read-only SQL (SELECT/WITH/SHOW/EXPLAIN)")

    params = arguments.get("params") or []
    if not isinstance(params, list):
        raise ValueError("params must be an array")

    row_limit = max(1, min(500, int(arguments.get("limit") or 100)))
    parsed = urllib.parse.urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("DATABASE_URL must use a postgres:// or postgresql:// scheme")
    query = urllib.parse.parse_qs(parsed.query)
    host = parsed.hostname or "localhost"
    sslmode = str((query.get("sslmode") or [""])[0]).lower()
    ssl_context = None
    if sslmode not in {"disable", "false", "0"} and host not in {"localhost", "127.0.0.1"}:
        ssl_context = ssl.create_default_context()
    try:
        conn = pg8000.native.Connection(
            user=urllib.parse.unquote(parsed.username or ""),
            password=urllib.parse.unquote(parsed.password or ""),
            host=host,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") or None,
            ssl_context=ssl_context,
            timeout=30,
        )
        try:
            rows = conn.run(sql, params=params)
        finally:
            conn.close()
    except Exception as exc:
        fallback = _postgres_query_via_supabase(sql=sql, row_limit=row_limit)
        if fallback is None:
            raise ValueError(f"postgres_query failed: {exc}") from exc
        fallback["warning"] = f"Direct DATABASE_URL query failed; used Supabase REST fallback: {type(exc).__name__}"
        return fallback

    normalized: list[Any] = []
    if isinstance(rows, list):
        normalized = rows[:row_limit]
    return {"row_count": len(normalized), "rows": normalized}


def _postgres_query_via_supabase(*, sql: str, row_limit: int) -> dict[str, Any] | None:
    info_match = _INFO_SCHEMA_TABLES_RE.match(sql)
    if info_match:
        limit = min(row_limit, int(info_match.group("limit") or row_limit))
        tables = _supabase_openapi_tables()[:limit]
        return {"row_count": len(tables), "rows": tables, "via": "supabase_openapi"}

    match = _SIMPLE_SELECT_RE.match(sql)
    if not match:
        return None
    select = (match.group("select") or "*").strip()
    table = _require_identifier(match.group("table") or "", "table")
    where_clause = (match.group("where") or "").strip()
    limit = min(row_limit, int(match.group("limit") or row_limit))
    filters = _parse_simple_where_filters(where_clause)
    rows = _supabase_query(
        {"table": table, "select": select, "limit": limit, "filters": filters},
        None,  # type: ignore[arg-type]
    )["rows"]
    return {"row_count": len(rows), "rows": rows, "via": "supabase_rest"}


def _supabase_openapi_tables() -> list[dict[str, Any]]:
    base_url, headers = _supabase_headers()
    openapi = _http_json(
        "GET",
        f"{base_url}/rest/v1/",
        headers={**headers, "Accept": "application/openapi+json"},
    )
    paths = openapi.get("paths") if isinstance(openapi, dict) else {}
    if not isinstance(paths, dict):
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(paths):
        if not isinstance(path, str) or path in {"/"}:
            continue
        table_name = path.strip("/").split("/", 1)[0]
        if not table_name or table_name.startswith("rpc/"):
            continue
        rows.append({"table_schema": "public", "table_name": table_name})
    return rows


def _parse_simple_where_filters(where_clause: str) -> dict[str, Any]:
    if not where_clause:
        return {}
    filters: dict[str, Any] = {}
    parts = re.split(r"\s+and\s+", where_clause, flags=re.IGNORECASE)
    for part in parts:
        match = re.match(r'^\s*"?(?P<col>[A-Za-z_][A-Za-z0-9_]*)"?\s*=\s*(?P<value>.+?)\s*$', part, flags=re.DOTALL)
        if not match:
            raise ValueError("postgres_query fallback only supports simple equality WHERE clauses joined by AND")
        column = _require_identifier(match.group("col"), "filter column")
        raw_value = match.group("value").strip()
        if raw_value.lower() == "null":
            value: Any = None
        elif raw_value.lower() in {"true", "false"}:
            value = raw_value.lower() == "true"
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            value = raw_value[1:-1].replace("''", "'")
        else:
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError as exc:
                    raise ValueError("postgres_query fallback only supports quoted strings, booleans, null, and numeric equality values") from exc
        filters[column] = value
    return filters


def builtin_data_access_tools(*, enable_supabase: bool = True, enable_postgres: bool = True) -> list[ToolDefinition]:
    tools: list[ToolDefinition] = []
    if enable_supabase:
        tools.extend([
            ToolDefinition(
            name="supabase_query",
            description="Query a Supabase table through the REST API using service credentials from env.",
            parameters={
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "select": {"type": "string"},
                    "limit": {"type": "integer"},
                    "filters": {"type": "object"},
                },
                "required": ["table"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_supabase_query,
        ),
        ToolDefinition(
            name="supabase_rpc",
            description="Call a Supabase PostgREST RPC function with JSON params.",
            parameters={
                "type": "object",
                "properties": {
                    "function": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["function"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=_supabase_rpc,
        ),
        ])
    if enable_postgres:
        tools.append(ToolDefinition(
            name="postgres_query",
            description="Run a read-only SQL query against DATABASE_URL and return rows.",
            parameters={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "params": {"type": "array", "items": {}},
                    "limit": {"type": "integer"},
                },
                "required": ["sql"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_postgres_query,
        ))
    return tools
