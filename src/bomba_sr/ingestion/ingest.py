"""Ingest a parsed document into memory stores + optionally Pinecone."""
from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)


def ingest_document(
    parsed: dict,
    tenant_id: str,
    user_id: str,
    being_id: str,
    filename: str,
    memory_store,
    consolidator,
    pinecone_index: str | None = None,
    pinecone_namespace: str | None = None,
) -> dict:
    """Store parsed document in local memory + optionally Pinecone.

    Returns summary of what was stored.
    """
    from bomba_sr.memory.consolidation import MemoryCandidate

    now = _utc_now()
    doc_id = uuid.uuid4().hex[:12]
    stored_chunks = 0
    stored_pinecone = 0

    # 1. Store full document as a markdown note
    memory_store.append_working_note(
        user_id=user_id,
        session_id=f"upload-{doc_id}",
        title=f"Uploaded: {filename}",
        content=parsed["markdown"][:50000],
        tags=["upload", parsed["metadata"]["format"], filename],
        confidence=1.0,
        being_id=being_id,
    )

    # 2. Store each chunk as a semantic memory
    for i, chunk in enumerate(parsed["chunks"]):
        consolidator.upsert(MemoryCandidate(
            user_id=f"{user_id}->prime->{being_id}",
            key=f"doc::{doc_id}::chunk-{i}",
            content=chunk,
            tier="semantic",
            evidence_refs=(f"upload://{filename}#chunk-{i}",),
            recency_ts=now,
            being_id=being_id,
        ))
        stored_chunks += 1

    # 3. Store tables as separate semantic memories
    for i, table in enumerate(parsed.get("tables", [])):
        consolidator.upsert(MemoryCandidate(
            user_id=f"{user_id}->prime->{being_id}",
            key=f"doc::{doc_id}::table-{i}",
            content=f"Table from {filename}:\n{table['csv'][:5000]}",
            tier="semantic",
            evidence_refs=(f"upload://{filename}#table-{i}",),
            recency_ts=now,
            being_id=being_id,
        ))

    # Commit local memory writes
    try:
        consolidator.db.commit()
    except Exception:
        pass

    # 4. Optionally embed chunks into Pinecone
    if pinecone_index and pinecone_namespace:
        try:
            from bomba_sr.tools.builtin_pinecone import (
                _choose_pinecone_api_key,
                _embed_batch,
                _http_json,
                _resolve_index_host,
            )
            api_key = _choose_pinecone_api_key(pinecone_index)
            host = _resolve_index_host(pinecone_index, api_key)

            texts = parsed["chunks"]
            if texts:
                vectors = _embed_batch(texts)
                pinecone_vectors = []
                for j, (text, vec) in enumerate(zip(texts, vectors)):
                    pinecone_vectors.append({
                        "id": f"doc-{doc_id}-{j}",
                        "values": vec,
                        "metadata": {
                            "text": text,
                            "tenant_id": tenant_id,
                            "being_id": being_id,
                            "source": f"upload://{filename}",
                            "chunk_index": j,
                        },
                    })

                payload = {"vectors": pinecone_vectors, "namespace": pinecone_namespace}
                url = f"https://{host}/vectors/upsert"
                resp = _http_json("POST", url, headers={"Api-Key": api_key}, payload=payload)
                stored_pinecone = resp.get("upsertedCount", len(pinecone_vectors))
        except Exception as exc:
            log.warning("Pinecone upsert failed: %s", exc)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks": stored_chunks,
        "tables": len(parsed.get("tables", [])),
        "pinecone_vectors": stored_pinecone,
        "markdown_length": len(parsed["markdown"]),
    }


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
