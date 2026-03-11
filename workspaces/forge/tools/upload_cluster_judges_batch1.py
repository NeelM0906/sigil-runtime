#!/usr/bin/env python3
"""
Upload Batch 1 canon cluster judges to acti-judges Pinecone
Namespace: cluster_judges_batch1
Metadata: type=cluster_judge, batch=1, status=canon

Usage: python3 upload_cluster_judges_batch1.py
"""

import os
import sys
import json
import time
import re
import urllib.request
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("~/.openclaw/workspace")
CLUSTER_JUDGES_DIR = WORKSPACE / "reports" / "judge-profiles" / "cluster-judges"
NAMESPACE = "cluster_judges_batch1"

CANON_FILES = [
    "d1-sc1-short-form-persuasion.md",
    "d1-sc3-conversion-copy.md",
    "d1-sc4-sequence-architecture.md",
    "d4-sc2-media-buying-budget.md",
    "d5-sc1-sales-conversations.md",
]

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
PINECONE_INDEX_HOST = "https://acti-judges-hw65sks.svc.aped-4627-b74a.pinecone.io"
EMBED_MODEL = "text-embedding-3-small"


def get_embedding(text: str) -> list:
    url = "https://openrouter.ai/api/v1/embeddings"
    payload = json.dumps({
        "model": EMBED_MODEL,
        "input": text[:8000]
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
        return data["data"][0]["embedding"]


def upsert_vectors(vectors: list):
    # Upsert in batches of 100 to avoid payload limits
    batch_size = 100
    results = []
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        url = f"{PINECONE_INDEX_HOST}/vectors/upsert"
        payload = json.dumps({"vectors": batch, "namespace": NAMESPACE}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            results.append(json.load(resp))
    return results


def chunk_judge_file(text: str, filename: str) -> list:
    """Split by ## sections, return list of (chunk_id, section_title, chunk_text)."""
    chunks = []
    sections = re.split(r'\n(?=## )', text)
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        title_match = re.match(r'## (.+)', section)
        title = title_match.group(1).strip() if title_match else f"section_{i}"
        raw_id = f"{filename.replace('.md','')}__{title.lower().replace(' ','_').replace('/','_')}"
        chunk_id = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_id)[:100]
        chunks.append((chunk_id, title, section.strip()))
    return chunks


def spot_check(query: str):
    """Query the namespace to verify upload landed."""
    embed = get_embedding(query)
    url = f"{PINECONE_INDEX_HOST}/query"
    payload = json.dumps({
        "vector": embed,
        "topK": 3,
        "namespace": NAMESPACE,
        "includeMetadata": True
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    if not PINECONE_API_KEY or not OPENROUTER_API_KEY:
        print("❌ Missing PINECONE_API_KEY or OPENROUTER_API_KEY")
        sys.exit(1)

    print(f"⚔️  Uploading Batch 1 cluster judges → acti-judges/{NAMESPACE}")
    print(f"   Source: {CLUSTER_JUDGES_DIR}")
    print()

    total_vectors = 0
    errors = 0

    for fname in CANON_FILES:
        fpath = CLUSTER_JUDGES_DIR / fname
        if not fpath.exists():
            print(f"❌ NOT FOUND: {fpath}")
            errors += 1
            continue

        text = fpath.read_text()
        chunks = chunk_judge_file(text, fname)
        print(f"📄 {fname} → {len(chunks)} chunks")

        file_vectors = []
        for chunk_id, section_title, chunk_text in chunks:
            try:
                embedding = get_embedding(chunk_text)
                file_vectors.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "type": "cluster_judge",
                        "batch": "1",
                        "status": "canon",
                        "file": fname,
                        "section": section_title,
                        "canonical_path": f"reports/judge-profiles/cluster-judges/{fname}",
                        "uploaded_at": datetime.utcnow().isoformat()
                    }
                })
                print(f"   ✅ {section_title[:60]}")
                time.sleep(0.2)
            except Exception as e:
                print(f"   ❌ {section_title}: {e}")
                errors += 1

        if file_vectors:
            result = upsert_vectors(file_vectors)
            total_vectors += len(file_vectors)
            print(f"   → Upserted {len(file_vectors)} vectors. Pinecone: {result}")

        print()

    print(f"{'='*60}")
    print(f"✅ Batch 1 upload complete")
    print(f"   Total vectors: {total_vectors}")
    print(f"   Errors: {errors}")
    print(f"   Namespace: {NAMESPACE}")
    print()

    # Spot check
    print("🔍 Spot-check retrieval...")
    try:
        result = spot_check("conversion copy judge scoring rubric 9.0 agreement formation")
        matches = result.get("matches", [])
        print(f"   Top {len(matches)} results:")
        for m in matches:
            print(f"   - [{m['score']:.3f}] {m['metadata'].get('file','')} / {m['metadata'].get('section','')}")
        if any(m['metadata'].get('type') == 'cluster_judge' for m in matches):
            print("   ✅ Retrieval confirmed — cluster judges are live in Pinecone")
        else:
            print("   ⚠️  Retrieval returned results but type mismatch — check namespace")
    except Exception as e:
        print(f"   ❌ Spot-check failed: {e}")


if __name__ == "__main__":
    main()
