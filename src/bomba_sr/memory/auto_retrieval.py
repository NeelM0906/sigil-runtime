"""Auto-retrieve relevant knowledge from Pinecone on every turn."""
from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from auto-retrieval, injected into context."""
    saimemory_results: list[dict[str, Any]]
    ublib2_results: list[dict[str, Any]]
    latency_ms: int
    query: str

    @property
    def has_results(self) -> bool:
        return bool(self.saimemory_results or self.ublib2_results)

    def format_context_block(self) -> str:
        """Format as XML block for injection into system prompt."""
        if not self.has_results:
            return ""

        parts = []
        parts.append(f'<knowledge_retrieval query="{self.query[:100]}" latency_ms="{self.latency_ms}">')

        if self.saimemory_results:
            parts.append('  <operational_memory source="saimemory">')
            for i, r in enumerate(self.saimemory_results[:5]):
                score = r.get("score", 0)
                text = r.get("text", "")[:500]
                source = r.get("source_namespace", "")
                parts.append(f'    <result rank="{i+1}" score="{score:.3f}" namespace="{source}">{text}</result>')
            parts.append("  </operational_memory>")

        if self.ublib2_results:
            parts.append('  <methodology source="ublib2">')
            for i, r in enumerate(self.ublib2_results[:5]):
                score = r.get("score", 0)
                text = r.get("text", "")[:500]
                parts.append(f'    <result rank="{i+1}" score="{score:.3f}">{text}</result>')
            parts.append("  </methodology>")

        parts.append("</knowledge_retrieval>")
        return "\n".join(parts)

    def format_sources_summary(self) -> list[dict[str, Any]]:
        """Format for the frontend sources indicator."""
        sources = []
        for r in self.saimemory_results[:5]:
            sources.append({
                "index": "saimemory",
                "namespace": r.get("source_namespace", ""),
                "score": round(r.get("score", 0), 3),
                "preview": (r.get("text", ""))[:100],
            })
        for r in self.ublib2_results[:5]:
            sources.append({
                "index": "ublib2",
                "score": round(r.get("score", 0), 3),
                "preview": (r.get("text", ""))[:100],
            })
        return sources


_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pinecone-auto")


def auto_retrieve(
    query: str,
    tenant_id: str,
    being_id: str | None = None,
    saimemory_namespace: str | None = None,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> RetrievalResult:
    """Query saimemory + ublib2 in parallel and return merged results."""
    from bomba_sr.tools.builtin_pinecone import (
        _embed_query,
        _choose_pinecone_api_key,
        _resolve_index_host,
        _http_json,
        _load_tenant_pinecone_map,
    )

    start = time.time()

    tenant_cfg = _load_tenant_pinecone_map().get(tenant_id, {})
    sai_index = tenant_cfg.get("index", "saimemory")
    sai_namespace = saimemory_namespace or tenant_cfg.get("namespace", "recovery")

    try:
        api_key_sai = _choose_pinecone_api_key(sai_index)
    except (ValueError, KeyError):
        return RetrievalResult([], [], 0, query)

    try:
        vector = _embed_query(query)
    except Exception as exc:
        log.debug("Auto-retrieval embedding failed: %s", exc)
        return RetrievalResult([], [], 0, query)

    def _search_index(index_name: str, namespace: str | None, api_key: str) -> list[dict]:
        try:
            host = _resolve_index_host(index_name, api_key)
            payload: dict[str, Any] = {
                "vector": vector,
                "topK": top_k,
                "includeMetadata": True,
            }
            if namespace:
                payload["namespace"] = namespace
            resp = _http_json(
                "POST",
                f"https://{host}/query",
                headers={"Api-Key": api_key},
                payload=payload,
            )
            results = []
            for m in resp.get("matches", []):
                score = float(m.get("score", 0))
                if score < score_threshold:
                    continue
                meta = m.get("metadata", {})
                results.append({
                    "id": m.get("id", ""),
                    "score": score,
                    "text": meta.get("text", meta.get("content", "")),
                    "source_namespace": namespace or "",
                    "being_id": meta.get("being_id"),
                    "tenant_id": meta.get("tenant_id"),
                })
            return results
        except Exception as exc:
            log.debug("Auto-retrieval search failed for %s/%s: %s", index_name, namespace, exc)
            return []

    saimemory_results: list[dict] = []
    ublib2_results: list[dict] = []

    try:
        api_key_ublib2 = _choose_pinecone_api_key("ublib2")
    except (ValueError, KeyError):
        api_key_ublib2 = None

    futures = {
        "saimemory": _POOL.submit(_search_index, sai_index, sai_namespace, api_key_sai),
        "saimemory_daily": _POOL.submit(_search_index, sai_index, "daily", api_key_sai),
    }
    if api_key_ublib2:
        futures["ublib2"] = _POOL.submit(_search_index, "ublib2", None, api_key_ublib2)

    for name, future in futures.items():
        try:
            results = future.result(timeout=5)
            if name.startswith("saimemory"):
                saimemory_results.extend(results)
            elif name == "ublib2":
                ublib2_results = results
        except Exception:
            pass

    # Deduplicate saimemory results
    seen_texts: set[str] = set()
    deduped_sai: list[dict] = []
    for r in sorted(saimemory_results, key=lambda x: x["score"], reverse=True):
        text_key = r["text"][:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            deduped_sai.append(r)

    latency_ms = int((time.time() - start) * 1000)
    log.info(
        "[AUTO-RETRIEVAL] query='%s' saimemory=%d ublib2=%d (%dms)",
        query[:60], len(deduped_sai), len(ublib2_results), latency_ms,
    )

    return RetrievalResult(
        saimemory_results=deduped_sai[:top_k],
        ublib2_results=ublib2_results[:top_k],
        latency_ms=latency_ms,
        query=query,
    )
