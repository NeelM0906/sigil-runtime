#!/usr/bin/env python3
"""Perplexity/Web enrichment → Translator → upsert into acti-judges.

Design goals:
- Additive only: does NOT overwrite existing 8-section mastery vectors.
- Produces extra vectors in the SAME namespace with section label: "TECHNICAL MASTERY (WEB-GROUNDED)".
- Sources are web_search-style summaries + citations; then Translator strips labels.

Usage:
  source .venv/bin/activate
  python tools/perplexity_enrich_acti_judges.py --namespace api-development-and-system-integration \
    --topic "API development and system integration" \
    --queries-file tools/perplexity_queries_api.txt

Env:
- OPENROUTER_API_KEY (for embeddings + translator LLM)
- PINECONE_API_KEY (acti-judges)

Note: This script calls the OpenRouter embeddings endpoint and Pinecone upsert directly.
"""

import os, sys, json, time, argparse, urllib.request
from datetime import datetime
from pathlib import Path

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
PINECONE_INDEX_HOST = "https://acti-judges-hw65sks.svc.aped-4627-b74a.pinecone.io"
EMBED_MODEL = "text-embedding-3-small"
SECTION = "TECHNICAL MASTERY (WEB-GROUNDED)"


def get_embedding(text: str) -> list:
    url = "https://openrouter.ai/api/v1/embeddings"
    payload = json.dumps({"model": EMBED_MODEL, "input": text[:8000]}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
        return data["data"][0]["embedding"]


def upsert_vectors(vectors: list, namespace: str):
    url = f"{PINECONE_INDEX_HOST}/vectors/upsert"
    payload = json.dumps({"vectors": vectors, "namespace": namespace}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Api-Key": PINECONE_API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespace", required=True, help="acti-judges namespace to enrich")
    ap.add_argument("--topic", required=True, help="Human-readable topic")
    ap.add_argument("--input-json", required=True, help="Translator output JSON file (mode=json)")
    ap.add_argument("--source", default="web", help="source tag")
    args = ap.parse_args()

    if not PINECONE_API_KEY or not OPENROUTER_API_KEY:
        print("ERROR: Missing PINECONE_API_KEY or OPENROUTER_API_KEY")
        sys.exit(1)

    p = Path(args.input_json)
    data = json.loads(p.read_text())

    vectors = []
    for i, section in enumerate(data, 1):
        # Translator v3 stores a dict per chunk with `raw` (string) and fields; we embed the raw json string.
        raw = section.get("raw", "")
        embed_text = f"TOPIC: {args.topic}\nSECTION: {SECTION}\nSOURCE: {args.source}\n\n{raw}"
        emb = get_embedding(embed_text)
        vid = f"{args.namespace}-web-{i:02d}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        vectors.append({
            "id": vid,
            "values": emb,
            "metadata": {
                "cluster": args.namespace,
                "domain": args.topic,
                "family": "web-grounded",
                "positions": 0,
                "lever": "",
                "section": SECTION,
                "text": raw[:1000],
                "uploaded_at": datetime.now().isoformat(),
                "source": args.source,
            },
        })
        time.sleep(0.5)

    res = upsert_vectors(vectors, args.namespace)
    print(json.dumps({"namespace": args.namespace, "vectors": len(vectors), "result": res}, indent=2)[:2000])


if __name__ == "__main__":
    main()
