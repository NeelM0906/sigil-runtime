from __future__ import annotations

import hashlib
import json
import logging
import re
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from bomba_sr.memory.hybrid import resolve_being_id
from bomba_sr.tools.base import ToolContext, ToolDefinition

log = logging.getLogger(__name__)


PINECONE_CONTROL_API = "https://api.pinecone.io/indexes"
OPENAI_EMBEDDINGS_API = "https://api.openai.com/v1/embeddings"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
INDEX_CACHE_TTL_SECONDS = 300.0
STRATA_INDEXES = {
    "oracleinfluencemastery",
    "ultimatestratabrain",
}
MAX_DESCRIBE_INDEXES = 20

_INDEX_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_INDEX_CACHE_LOCK = threading.Lock()
SAFE_INDEX_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

# ── Per-tenant Pinecone routing ──────────────────────────────────────
_TENANT_PINECONE_MAP: dict[str, dict] | None = None


def _load_tenant_pinecone_map() -> dict[str, dict]:
    global _TENANT_PINECONE_MAP
    if _TENANT_PINECONE_MAP is not None:
        return _TENANT_PINECONE_MAP
    from pathlib import Path
    map_path = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime")) / "tenant_pinecone_map.json"
    if map_path.exists():
        _TENANT_PINECONE_MAP = json.loads(map_path.read_text(encoding="utf-8"))
    else:
        _TENANT_PINECONE_MAP = {}
    return _TENANT_PINECONE_MAP


def reload_tenant_pinecone_map() -> None:
    """Force reload the tenant-pinecone map (e.g. after onboarding new users)."""
    global _TENANT_PINECONE_MAP
    _TENANT_PINECONE_MAP = None
    _load_tenant_pinecone_map()


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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
        except OSError:
            error_body = ""
        detail = f": {error_body[:200]}" if error_body else ""
        raise ValueError(f"Pinecone/OpenAI request failed (HTTP {exc.code}){detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Pinecone/OpenAI request failed: {exc.reason}") from exc
    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Pinecone/OpenAI endpoint returned invalid JSON") from exc


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
    cache_key = _cache_key_for_api_key(api_key)
    with _INDEX_CACHE_LOCK:
        cached = _INDEX_CACHE.get(cache_key)
    now = time.time()
    if cached is not None:
        ts, payload = cached
        if now - ts < INDEX_CACHE_TTL_SECONDS:
            return payload
    payload = _http_json("GET", PINECONE_CONTROL_API, headers={"Api-Key": api_key})
    if not isinstance(payload, dict):
        payload = {}
    with _INDEX_CACHE_LOCK:
        _INDEX_CACHE[cache_key] = (now, payload)
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
    cache_key = _cache_key_for_api_key(api_key)
    for force_refresh in (False, True):
        if force_refresh:
            with _INDEX_CACHE_LOCK:
                _INDEX_CACHE.pop(cache_key, None)
        payload = _list_indexes_with_cache(api_key)
        for item in _index_records(payload):
            if str(item.get("name") or "") == index_name:
                host = str(item.get("host") or "").strip()
                if host:
                    return _sanitize_index_host(host)
    fallback = _fallback_host_map().get(index_name)
    if isinstance(fallback, str) and fallback.strip():
        return _sanitize_index_host(fallback.strip())
    raise ValueError(f"Pinecone index host not found for '{index_name}'")


def _fallback_host_map() -> dict[str, str]:
    import os

    raw = os.getenv("BOMBA_PINECONE_INDEX_HOSTS", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
            out[key.strip()] = value.strip()
    return out


def _require_safe_index_name(index_name: str) -> str:
    cleaned = index_name.strip()
    if not cleaned:
        raise ValueError("index_name is required")
    if not SAFE_INDEX_PATTERN.fullmatch(cleaned):
        raise ValueError("index_name contains invalid characters")
    return cleaned


def _sanitize_index_host(host: str) -> str:
    cleaned = host.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        parsed = urllib.parse.urlparse(cleaned)
        cleaned = parsed.netloc.strip()
    if not cleaned:
        raise ValueError("invalid Pinecone host")
    if "/" in cleaned or "?" in cleaned or "#" in cleaned or "@" in cleaned:
        raise ValueError("invalid Pinecone host")
    if not re.fullmatch(r"[A-Za-z0-9.:-]+", cleaned):
        raise ValueError("invalid Pinecone host")
    return cleaned


def _cache_key_for_api_key(api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _embed_query(query: str) -> list[float]:
    api_key, api_base, embed_model = _embedding_settings()
    payload = _http_json(
        "POST",
        api_base.rstrip("/") + "/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        payload={"model": embed_model, "input": query},
    )
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("invalid embeddings response")
    first = data[0] if isinstance(data[0], dict) else {}
    vector = first.get("embedding")
    if not isinstance(vector, list):
        raise ValueError("missing embedding vector in embeddings response")
    return [float(x) for x in vector]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    api_key, api_base, embed_model = _embedding_settings()
    payload = _http_json(
        "POST",
        api_base.rstrip("/") + "/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        payload={"model": embed_model, "input": texts},
    )
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise ValueError("invalid batch embeddings response")
    sorted_data = sorted(data, key=lambda d: int(d.get("index", 0)) if isinstance(d, dict) else 0)
    vectors: list[list[float]] = []
    for item in sorted_data:
        if not isinstance(item, dict):
            raise ValueError("invalid embedding item in batch response")
        emb = item.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("missing embedding vector in batch response")
        vectors.append([float(x) for x in emb])
    return vectors


def _embedding_settings() -> tuple[str, str, str]:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    embed_model = (
        os.getenv("BOMBA_PINECONE_EMBED_MODEL")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or DEFAULT_EMBED_MODEL
    ).strip()
    # Prefer OpenAI directly for embeddings (more reliable than proxying through OpenRouter)
    if openai_key:
        return (
            openai_key,
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            embed_model,
        )
    if openrouter_key:
        return (
            openrouter_key,
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            "openai/text-embedding-3-small",
        )
    raise ValueError("OPENAI_API_KEY or OPENROUTER_API_KEY is required for Pinecone embeddings")


def _parse_matches(
    response: dict[str, Any],
    score_threshold: float,
    extra_fields: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Extract and filter matches from a Pinecone query response."""
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
        entry: dict[str, Any] = {
            "id": str(item.get("id") or ""),
            "score": score,
            "metadata": metadata,
            "text": text,
        }
        if extra_fields:
            entry.update(extra_fields)
        results.append(entry)
    return results


def _pinecone_query_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        # Tenant-specific index/namespace routing
        tenant_cfg = _load_tenant_pinecone_map().get(context.tenant_id, {})
        effective_index = tenant_cfg.get("index", default_index)
        effective_ns = tenant_cfg.get("namespace", default_namespace)
        index_name = _require_safe_index_name(str(arguments.get("index_name") or effective_index))
        namespace = arguments.get("namespace")
        # Only apply tenant namespace when querying the tenant's own index
        # (querying a different index like ublib2 should use that index's default ns)
        tenant_ns = effective_ns if index_name == effective_index else default_namespace
        namespace_value = (
            str(namespace).strip()
            if namespace is not None and str(namespace).strip()
            else (tenant_ns or None)
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
        # Build metadata filter: tenant scoping + optional caller filter
        tenant_id = context.tenant_id
        caller_filter = arguments.get("filter")
        if not isinstance(caller_filter, dict):
            caller_filter = None
        if tenant_id:
            tenant_clause = {"tenant_id": {"$eq": tenant_id}}
            if caller_filter:
                payload["filter"] = {"$and": [tenant_clause, caller_filter]}
            else:
                payload["filter"] = tenant_clause
        elif caller_filter:
            payload["filter"] = caller_filter
        url = f"https://{host}/query"
        response = _http_json("POST", url, headers={"Api-Key": api_key}, payload=payload)

        results = _parse_matches(response, score_threshold)

        # Fallback: if scoped query returned nothing, retry without tenant filter
        legacy_fallback = False
        if not results and tenant_id and "filter" in payload:
            unscoped_payload = {k: v for k, v in payload.items() if k != "filter"}
            if caller_filter:
                unscoped_payload["filter"] = caller_filter
            fallback_resp = _http_json("POST", url, headers={"Api-Key": api_key}, payload=unscoped_payload)
            results = _parse_matches(fallback_resp, score_threshold)
            if results:
                legacy_fallback = True
                log.warning(
                    "Legacy unscoped vectors returned for index=%s namespace=%s — consider re-indexing",
                    index_name, namespace_value,
                )

        out: dict[str, Any] = {
            "query": query,
            "index_name": index_name,
            "namespace": namespace_value,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "results": results,
        }
        if legacy_fallback:
            out["legacy_fallback"] = True
        return out

    return run


def _pinecone_list_indexes_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = arguments
        _ = context
        api_key = _choose_pinecone_api_key(default_index)
        payload = _list_indexes_with_cache(api_key)
        indexes = _index_records(payload)
        out: list[dict[str, Any]] = []
        for idx, item in enumerate(indexes):
            name = str(item.get("name") or "")
            host = str(item.get("host") or "")
            stats: dict[str, Any] = {}
            vector_count = 0
            if host and idx < MAX_DESCRIBE_INDEXES:
                try:
                    query: dict[str, Any] = {}
                    # Only pass namespace for the tenant's own default index
                    if default_namespace and name == default_index:
                        query["namespace"] = default_namespace
                    # Use the correct API key per index (may differ for STRATA)
                    idx_key = _choose_pinecone_api_key(name) if name else api_key
                    stats = _http_json(
                        "POST",
                        f"https://{host}/describe_index_stats",
                        headers={"Api-Key": idx_key},
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


def _pinecone_upsert_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        texts = arguments.get("texts")
        if not isinstance(texts, list) or not texts:
            raise ValueError("texts is required and must be a non-empty array of strings")
        texts = [str(t) for t in texts]
        # Tenant-specific index/namespace routing
        tenant_cfg = _load_tenant_pinecone_map().get(context.tenant_id, {})
        effective_index = tenant_cfg.get("index", default_index)
        effective_ns = tenant_cfg.get("namespace", default_namespace)
        index_name = _require_safe_index_name(str(arguments.get("index_name") or effective_index))
        namespace = arguments.get("namespace")
        tenant_ns = effective_ns if index_name == effective_index else default_namespace
        namespace_value = (
            str(namespace).strip()
            if namespace is not None and str(namespace).strip()
            else (tenant_ns or None)
        )
        extra_metadata = arguments.get("metadata") or {}
        if not isinstance(extra_metadata, dict):
            extra_metadata = {}
        id_prefix = str(arguments.get("id_prefix") or "bomba").strip()

        api_key = _choose_pinecone_api_key(index_name)
        host = _resolve_index_host(index_name, api_key)
        vectors_data = _embed_batch(texts)

        # Inject tenant/being scoping metadata
        tenant_id = context.tenant_id
        being_id = resolve_being_id(context.session_id, context.user_id)

        pinecone_vectors: list[dict[str, Any]] = []
        for text, embedding in zip(texts, vectors_data):
            vec_id = f"{id_prefix}-{uuid.uuid4().hex[:12]}"
            meta = {
                "text": text,
                "tenant_id": tenant_id or None,
                "being_id": being_id,  # may be None
                "user_id": context.user_id,
                "session_id": context.session_id,
                **extra_metadata,
            }
            pinecone_vectors.append({
                "id": vec_id,
                "values": embedding,
                "metadata": meta,
            })

        upsert_payload: dict[str, Any] = {"vectors": pinecone_vectors}
        if namespace_value:
            upsert_payload["namespace"] = namespace_value

        url = f"https://{host}/vectors/upsert"
        response = _http_json("POST", url, headers={"Api-Key": api_key}, payload=upsert_payload)
        upserted = response.get("upsertedCount", len(pinecone_vectors))
        return {
            "upserted_count": int(upserted),
            "index_name": index_name,
            "namespace": namespace_value,
        }

    return run


def _pinecone_multi_query_factory(default_index: str, default_namespace: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        indexes = arguments.get("indexes")
        if not isinstance(indexes, list) or not indexes:
            raise ValueError("indexes is required and must be a non-empty array")
        top_k = max(1, min(20, int(arguments.get("top_k") or 5)))
        # Tenant-specific default namespace
        tenant_cfg = _load_tenant_pinecone_map().get(context.tenant_id, {})
        tenant_index = tenant_cfg.get("index", default_index)
        tenant_ns = tenant_cfg.get("namespace", default_namespace)
        score_threshold = float(arguments.get("score_threshold") or 0.4)

        vector = _embed_query(query)
        # Capture tenant for sub-query scoping
        tenant_id = context.tenant_id

        def _query_one(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
            idx_name = _require_safe_index_name(str(spec.get("index_name") or ""))
            ns = spec.get("namespace")
            # Only apply tenant namespace for the tenant's own index
            effective_ns = tenant_ns if idx_name == tenant_index else default_namespace
            ns_value = (
                str(ns).strip()
                if ns is not None and str(ns).strip()
                else (effective_ns or None)
            )
            api_key = _choose_pinecone_api_key(idx_name)
            host = _resolve_index_host(idx_name, api_key)
            payload: dict[str, Any] = {
                "vector": vector,
                "topK": top_k,
                "includeMetadata": True,
            }
            if ns_value:
                payload["namespace"] = ns_value
            # Tenant scoping + optional per-index caller filter
            per_index_filter = spec.get("filter")
            if not isinstance(per_index_filter, dict):
                per_index_filter = None
            if tenant_id:
                tenant_clause = {"tenant_id": {"$eq": tenant_id}}
                if per_index_filter:
                    payload["filter"] = {"$and": [tenant_clause, per_index_filter]}
                else:
                    payload["filter"] = tenant_clause
            elif per_index_filter:
                payload["filter"] = per_index_filter
            url = f"https://{host}/query"
            resp = _http_json("POST", url, headers={"Api-Key": api_key}, payload=payload)
            extras = {"source_index": idx_name, "source_namespace": ns_value}
            results = _parse_matches(resp, score_threshold, extra_fields=extras)

            # Fallback for legacy unscoped vectors
            if not results and tenant_id and "filter" in payload:
                unscoped = {k: v for k, v in payload.items() if k != "filter"}
                if per_index_filter:
                    unscoped["filter"] = per_index_filter
                fallback_resp = _http_json("POST", url, headers={"Api-Key": api_key}, payload=unscoped)
                results = _parse_matches(fallback_resp, score_threshold, extra_fields=extras)
                if results:
                    log.warning(
                        "Legacy unscoped vectors returned for index=%s namespace=%s — consider re-indexing",
                        idx_name, ns_value,
                    )
            return idx_name, results

        all_results: list[dict[str, Any]] = []
        indexes_queried: list[str] = []
        errors: list[dict[str, str]] = []
        with ThreadPoolExecutor(max_workers=min(len(indexes), 8)) as pool:
            futures = {pool.submit(_query_one, spec): spec for spec in indexes}
            for future in as_completed(futures):
                spec = futures[future]
                idx_name = str(spec.get("index_name") or "unknown")
                try:
                    queried_name, results = future.result()
                    indexes_queried.append(queried_name)
                    all_results.extend(results)
                except Exception as exc:
                    errors.append({"index": idx_name, "error": str(exc)})

        all_results.sort(key=lambda r: r.get("score", 0.0), reverse=True)

        seen_texts: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for r in all_results:
            text_key = r.get("text", "")
            if text_key and text_key in seen_texts:
                continue
            if text_key:
                seen_texts.add(text_key)
            deduped.append(r)

        out: dict[str, Any] = {
            "query": query,
            "indexes_queried": indexes_queried,
            "results": deduped,
        }
        if errors:
            out["errors"] = errors
        return out

    return run


def builtin_pinecone_tools(default_index: str = "ublib2", default_namespace: str | None = "longterm") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="pinecone_query",
            description=(
                "Search your knowledge bases for information from past conversations, "
                "uploaded documents, case data, contracts, and institutional knowledge. "
                "USE THIS when you need to recall specific facts, case details, contract "
                "terms, fee schedules, carrier information, or methodology that isn't in "
                "your immediate conversation history. "
                "Default searches your operational memory (saimemory). "
                "Pass index_name='ublib2' to search the master knowledge library for "
                "coaching frameworks, business methodology, and the Formula."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language search query — describe what you're looking for."},
                    "index_name": {
                        "type": "string",
                        "description": "Which knowledge base: 'saimemory' (default, operational memory) or 'ublib2' (master methodology library). Omit for default.",
                    },
                    "namespace": {
                        "type": ["string", "null"],
                        "description": "Namespace within the index. For saimemory: 'recovery' (case data), 'daily' (daily learnings), 'continuity-transfer' (identity). For ublib2: usually omit. Omit for your default.",
                    },
                    "top_k": {"type": "integer", "description": "Maximum matches to return (1-20, default 5)."},
                    "score_threshold": {"type": "number", "description": "Minimum similarity score (default 0.4)."},
                    "filter": {"type": "object", "description": "Optional Pinecone metadata filter."},
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
            description=(
                "List available Pinecone indexes and their stats. Use to verify "
                "which knowledge bases are accessible and how many vectors they contain."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_pinecone_list_indexes_factory(default_index=default_index, default_namespace=default_namespace),
        ),
        ToolDefinition(
            name="pinecone_upsert",
            description=(
                "Store important information as vectors in your knowledge base for "
                "long-term recall. Use this when you learn something that should persist "
                "across sessions — case outcomes, contract patterns, process improvements, "
                "key decisions."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Text chunks to embed and store.",
                    },
                    "index_name": {"type": "string", "description": "Target index (default: saimemory)."},
                    "namespace": {"type": ["string", "null"], "description": "Target namespace (default: your configured namespace)."},
                    "metadata": {"type": "object", "description": "Additional metadata to attach to each vector."},
                    "id_prefix": {"type": "string", "description": "Prefix for vector IDs (default: 'bomba')."},
                },
                "required": ["texts"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_pinecone_upsert_factory(default_index=default_index, default_namespace=default_namespace),
        ),
        ToolDefinition(
            name="pinecone_multi_query",
            description=(
                "Search BOTH your operational memory AND the master knowledge library "
                "in a single call. Use when you need comprehensive results — for example, "
                "analyzing a case (saimemory) while grounding your approach in methodology (ublib2). "
                "Returns merged results ranked by relevance."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language search query."},
                    "indexes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index_name": {"type": "string", "description": "Index name: 'saimemory' or 'ublib2'."},
                                "namespace": {"type": ["string", "null"], "description": "Namespace within the index."},
                            },
                            "required": ["index_name"],
                        },
                        "description": "Indexes to search. Example: [{\"index_name\": \"saimemory\"}, {\"index_name\": \"ublib2\"}]",
                    },
                    "top_k": {"type": "integer", "description": "Maximum matches per index (1-20)."},
                    "score_threshold": {"type": "number", "description": "Minimum similarity score."},
                },
                "required": ["query", "indexes"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_pinecone_multi_query_factory(default_index=default_index, default_namespace=default_namespace),
        ),
    ]
