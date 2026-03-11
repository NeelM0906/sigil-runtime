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


query = "Unblinded Formula Sean Callagy 4 Steps Influence 7 Destroyers Self Mastery"
vec = embed(query)

idx_name = sys.argv[1] if len(sys.argv) > 1 else "ublib2"
print(f"=== {idx_name} ===")
idx = pc.Index(idx_name)

results = idx.query(vector=vec, top_k=5, include_metadata=True)
for hit in results.matches:
    meta = hit.metadata if hit.metadata else {}
    text = meta.get("text", meta.get("content", meta.get("chunk_text", meta.get("page_content", ""))))
    if not text:
        text = str(meta)[:400]
    print(f"\nScore: {hit.score:.4f} | ID: {hit.id[:60]}")
    print(f"Text: {str(text)[:350]}")
    print("---")
