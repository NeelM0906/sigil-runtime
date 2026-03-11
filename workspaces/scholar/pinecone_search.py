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
    "Unblinded Formula 4 Steps of Influence 7 Destroyers 12 Indispensable Elements",
    "Sean Callagy Self Mastery Influence Mastery Process Mastery three masteries",
    "7 Levers marketing sales process mastery ecosystem mergers",
    "4 Energies Fun Aspirational Goddess Zeus influence",
    "39 components Unblinded Results Formula Liberators",
]

indexes_to_search = [
    "ublib2",
    "athenacontextualmemory",
    "stratablue",
    "saimemory",
    "seanmiracontextualmemory",
    "adamathenacontextualmemory",
    "seancallieupdates",
    "miracontextualmemory",
]

idx_name = sys.argv[1] if len(sys.argv) > 1 else indexes_to_search[0]
print(f"\n=== SEARCHING: {idx_name} ===")
idx = pc.Index(idx_name)

for query in queries:
    vec = embed(query)
    try:
        results = idx.query(vector=vec, top_k=3, include_metadata=True)
        hits = results.matches
        if hits and hits[0].score > 0.75:
            print(f"\nQuery: {query[:60]}...")
            for hit in hits:
                meta = hit.metadata if hit.metadata else {}
                text = meta.get("text", meta.get("content", meta.get("chunk_text", "")))[:300]
                print(f"  Score: {hit.score:.4f} | ID: {hit.id[:50]}")
                if text:
                    print(f"  Text: {text[:250]}...")
    except Exception as exc:
        print(f"  Error: {exc}")
