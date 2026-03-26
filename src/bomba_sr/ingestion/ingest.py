"""Ingest extracted document text into memory stores + optionally Pinecone."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def ingest_to_memory(
    extracted: dict,
    tenant_id: str,
    user_id: str,
    being_id: str,
    filename: str,
    memory_store,
    consolidator,
) -> dict:
    """Store extracted document text in local memory. Returns summary."""
    from bomba_sr.ingestion.parser import chunk_text
    from bomba_sr.memory.consolidation import MemoryCandidate

    now = datetime.now(timezone.utc).isoformat()
    doc_id = uuid.uuid4().hex[:12]
    text = extracted.get("text") or ""
    is_placeholder = extracted.get("_is_native_placeholder", False)

    if text.strip() and not is_placeholder:
        # Real extracted text — store as working note + semantic chunks
        memory_store.append_working_note(
            user_id=user_id,
            session_id=f"upload-{doc_id}",
            title=f"Uploaded: {filename}",
            content=text[:50000],
            tags=["upload", extracted.get("format", ""), filename],
            confidence=1.0,
            being_id=being_id,
        )

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            consolidator.upsert(MemoryCandidate(
                user_id=f"{user_id}->prime->{being_id}",
                key=f"doc::{doc_id}::chunk-{i}",
                content=chunk,
                tier="semantic",
                evidence_refs=(f"upload://{filename}#chunk-{i}",),
                recency_ts=now,
                being_id=being_id,
            ))
    else:
        # Native/scanned file — store metadata-only record (no chunking/embedding)
        memory_store.append_working_note(
            user_id=user_id,
            session_id=f"upload-{doc_id}",
            title=f"Uploaded: {filename}",
            content=f"Scanned/native document uploaded: {filename}. "
                    f"File saved to workspace uploads directory. "
                    f"Use parse_document or exec with OCR to extract content.",
            tags=["upload", "native", extracted.get("format", ""), filename],
            confidence=0.5,
            being_id=being_id,
        )
        chunks = []

    try:
        consolidator.db.commit()
    except Exception:
        pass

    return {
        "doc_id": doc_id,
        "filename": filename,
        "text_length": len(text),
        "chunks": len(chunks),
        "format": extracted.get("format", ""),
    }


def ingest_to_pinecone_background(
    text: str,
    doc_id: str,
    tenant_id: str,
    being_id: str,
    filename: str,
    index: str,
    namespace: str,
) -> None:
    """Spawn background thread to chunk, embed, and upsert to Pinecone."""
    def _run():
        try:
            from bomba_sr.ingestion.parser import chunk_text
            from bomba_sr.tools.builtin_pinecone import (
                _choose_pinecone_api_key,
                _embed_batch,
                _http_json,
                _resolve_index_host,
            )

            chunks = chunk_text(text)
            if not chunks:
                return

            api_key = _choose_pinecone_api_key(index)
            host = _resolve_index_host(index, api_key)
            vectors_data = _embed_batch(chunks)

            pinecone_vectors = []
            for j, (chunk, vec) in enumerate(zip(chunks, vectors_data)):
                pinecone_vectors.append({
                    "id": f"doc-{doc_id}-{j}",
                    "values": vec,
                    "metadata": {
                        "text": chunk,
                        "tenant_id": tenant_id,
                        "being_id": being_id,
                        "source": f"upload://{filename}",
                        "chunk_index": j,
                    },
                })

            payload = {"vectors": pinecone_vectors, "namespace": namespace}
            url = f"https://{host}/vectors/upsert"
            _http_json("POST", url, headers={"Api-Key": api_key}, payload=payload)
            log.info("Pinecone: upserted %d vectors for %s", len(pinecone_vectors), filename)
        except Exception as exc:
            log.warning("Pinecone background ingest failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()
