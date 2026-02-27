from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


PINECONE_CONTROL_API = "https://api.pinecone.io/indexes"
OPENAI_EMBEDDINGS_API = "https://api.openai.com/v1/embeddings"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
INDEX_CACHE_TTL_SECONDS = 300.0
STRATA_INDEXES = {
    "oracleinfluencemastery",
    "ultimatestratabrain",
    "athenacontextualmemory",
}

_INDEX_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    data = None
    req_headers = {"Accept": "application/json", "User-Agent": "sigil-runtime/1.0"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=req_headers, method=method, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    if not body.strip():
        return {}
    return json.loads(body)


def _choose_pinecone_api_key(index_name: str) -> str:
    import os

    default_key = os.getenv("PINECONE_API_KEY", "").strip()
    strata_key = os.getenv("PINECONE_API_KEY_STRATA", "").strip()
    if index_name in STRATA_INDEXES and strata_key:
        return strata_key
    if default_key:
        return default_key
    raise ValueError("PINECONE_API_KEY is required")


def _list_indexes_with_cache(api_key: str) -> dict[str, Any]:
    cached = _INDEX_CACHE.get(api_key)
    now = time.time()
    if cached is not None:
        ts, payload = cached
        if now - ts < INDEX_CACHE_TTL_SECONDS:
            return payload
    payload = _http_json("GET", PINECONE_CONTROL_API, headers={"Api-Key": api_key})
    if not isinstance(payload, dict):
        payload = {}
    _INDEX_CACHE[api_key] = (now, payload)
    return payload


def _index_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("indexes")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [item for item in raw.values() if isinstance(item, dict)]
    if isinstance(payload.get("data"), list):
        return [item for item in payload["data"] if isinstance(item, dict)]
    return []


def _resolve_index_host(index_name: str, api_key: str) -> str:
    payload = _list_indexes_with_cache(api_key)
    for item in _index_records(payload):
        if str(item.get("name") or "") == index_name:
            host = str(item.get("host") or "").strip()
            if host:
                return host
    raise ValueError(f"Pinecone index host not found for '{index_name}'")


def _embed_query(query: str) -> list[float]:
    import os

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key:
        raise ValueError("OPENAI_API_KEY is required for pinecone_query embeddings")
    payload = _http_json(
        "POST",
        OPENAI_EMBEDDINGS_API,
        headers={"Authorization": f"Bearer {openai_key}"},
        payload={"model": DEFAULT_EMBED_MODEL, "input": query},
    )
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("invalid OpenAI embeddings response")
    first = data[0] if isinstance(data[0], dict) else {}
    vector = first.get("embedding")
    if not isinstance(vector, list):
        raise ValueError("missing embedding vector in OpenAI response")
    return [float(x) for x in vector]


def _pinecone_query_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        index_name = str(arguments.get("index_name") or default_index).strip()
        if not index_name:
            raise ValueError("index_name is required")
        namespace = arguments.get("namespace")
        namespace_value = (
            str(namespace).strip()
            if namespace is not None and str(namespace).strip()
            else (default_namespace or None)
        )
        top_k = max(1, min(20, int(arguments.get("top_k") or 5)))
        score_threshold = float(arguments.get("score_threshold") or 0.4)

        api_key = _choose_pinecone_api_key(index_name)
        host = _resolve_index_host(index_name, api_key)
        vector = _embed_query(query)
        payload: dict[str, Any] = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": True,
        }
        if namespace_value:
            payload["namespace"] = namespace_value
        url = f"https://{host}/query"
        response = _http_json("POST", url, headers={"Api-Key": api_key}, payload=payload)

        matches = response.get("matches")
        if not isinstance(matches, list):
            matches = []
        results: list[dict[str, Any]] = []
        for item in matches:
            if not isinstance(item, dict):
                continue
            score = float(item.get("score") or 0.0)
            if score < score_threshold:
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            text = (
                str(metadata.get("text") or "")
                or str(metadata.get("chunk") or "")
                or str(metadata.get("content") or "")
            )
            results.append(
                {
                    "id": str(item.get("id") or ""),
                    "score": score,
                    "metadata": metadata,
                    "text": text,
                }
            )
        return {
            "query": query,
            "index_name": index_name,
            "namespace": namespace_value,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "results": results,
        }

    return run


def _pinecone_list_indexes_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = arguments
        _ = context
        api_key = _choose_pinecone_api_key(default_index)
        payload = _list_indexes_with_cache(api_key)
        indexes = _index_records(payload)
        out: list[dict[str, Any]] = []
        for item in indexes:
            name = str(item.get("name") or "")
            host = str(item.get("host") or "")
            stats: dict[str, Any] = {}
            vector_count = 0
            if host:
                try:
                    query: dict[str, Any] = {}
                    if default_namespace:
                        query["namespace"] = default_namespace
                    stats = _http_json(
                        "POST",
                        f"https://{host}/describe_index_stats",
                        headers={"Api-Key": api_key},
                        payload=query,
                    )
                    if isinstance(stats.get("totalVectorCount"), int):
                        vector_count = int(stats.get("totalVectorCount"))
                    elif isinstance(stats.get("namespaces"), dict):
                        vector_count = sum(
                            int(ns.get("vectorCount") or 0)
                            for ns in stats["namespaces"].values()
                            if isinstance(ns, dict)
                        )
                except (urllib.error.URLError, ValueError, KeyError):
                    vector_count = 0
            out.append(
                {
                    "name": name,
                    "host": host,
                    "dimension": item.get("dimension"),
                    "metric": item.get("metric"),
                    "status": item.get("status"),
                    "vector_count": vector_count,
                }
            )
        return {"indexes": out}

    return run


def builtin_pinecone_tools(default_index: str = "ublib2", default_namespace: str | None = "longterm") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="pinecone_query",
            description="Query a Pinecone vector index using an embedded search query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "index_name": {"type": "string"},
                    "namespace": {"type": ["string", "null"]},
                    "top_k": {"type": "integer"},
                    "score_threshold": {"type": "number"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_pinecone_query_factory(default_index=default_index, default_namespace=default_namespace),
        ),
        ToolDefinition(
            name="pinecone_list_indexes",
            description="List accessible Pinecone indexes and vector counts.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            risk_level="low",
            action_type="read",
            execute=_pinecone_list_indexes_factory(default_index=default_index, default_namespace=default_namespace),
        ),
    ]
