#!/usr/bin/env python3
import os
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

names = [
    "ublib2",
    "athenacontextualmemory",
    "stratablue",
    "saimemory",
    "seanmiracontextualmemory",
    "uimira",
    "uicontextualmemory",
    "seancallieupdates",
    "kumar-requirements",
    "kumar-pfd",
    "012626bellavcalliememory",
    "adamathenacontextualmemory",
    "baslawyerathenacontextualmemory",
    "miracontextualmemory",
]

for name in names:
    try:
        idx = pc.Index(name)
        stats = idx.describe_index_stats()
        total = stats.total_vector_count
        namespaces = {key: value.vector_count for key, value in stats.namespaces.items()} if stats.namespaces else {}
        print(f"{name}: {total} vectors | ns: {namespaces}")
    except Exception as exc:
        print(f"{name}: ERROR - {exc}")
