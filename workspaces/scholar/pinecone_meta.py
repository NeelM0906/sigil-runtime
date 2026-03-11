#!/usr/bin/env python3
import os
import sys
from pathlib import Path

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

idx_name = sys.argv[1] if len(sys.argv) > 1 else "ublib2"
idx = pc.Index(idx_name)

sample_ids = ["255afc68-a12c-4c00-ba3c-7cd44a25c53a"]
result = idx.fetch(ids=sample_ids)
for vector_id, vector_data in result.vectors.items():
    print(f"ID: {vector_id}")
    meta = vector_data.metadata
    print(f"Metadata keys: {list(meta.keys())}")
    for key, value in meta.items():
        print(f"  {key}: {str(value)[:200]}")
    print(f"Vector dim: {len(vector_data.values)}")
