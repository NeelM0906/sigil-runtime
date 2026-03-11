#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from openai import OpenAI
from pinecone import Pinecone


def _load_repo_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_repo_env()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
oai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def embed(text: str):
    response = oai.embeddings.create(input=text, model="text-embedding-ada-002")
    return response.data[0].embedding


queries = [
    "Unblinded Formula 4 Steps of Influence",
    "7 Destroyers Self Mastery Liberators",
    "12 Indispensable Elements emotional rapport",
    "Process Mastery 7 Levers marketing sales",
    "4 Energies Fun Aspirational Goddess Zeus",
]

idx_name = sys.argv[1]
print(f"\n{'=' * 60}")
print(f"INDEX: {idx_name}")
print(f"{'=' * 60}")

idx = pc.Index(idx_name)

for query in queries:
    vec = embed(query)
    results = idx.query(vector=vec, top_k=2, include_metadata=True)
    best = results.matches[0] if results.matches else None
    if best:
        meta = best.metadata or {}
        text = meta.get("text", meta.get("content", meta.get("chunk_text", meta.get("page_content", str(meta)[:300]))))
        print(f"\nQ: {query}")
        print(f"  Best Score: {best.score:.4f}")
        print(f"  Text: {str(text)[:300]}")
