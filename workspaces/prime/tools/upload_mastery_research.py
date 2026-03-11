#!/usr/bin/env python3
"""
Upload 80 mastery research JSONs to Pinecone saimemory index.
Namespace: position_mastery
Each position becomes one vector with rich metadata.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Use the workspace .venv
VENV_PYTHON = "~/.openclaw/.venv/bin/python"
VENV_DIR = os.path.dirname(os.path.dirname(VENV_PYTHON))
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.prefix) != os.path.realpath(VENV_DIR):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

from pinecone import Pinecone
import urllib.request

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
INDEX_NAME = "acti-judges"
NAMESPACE = "position_mastery"
EMBED_MODEL = "openai/text-embedding-3-small"
RESEARCH_DIR = Path("~/.openclaw/workspace/reports/mastery-research")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)


def get_embedding(text: str) -> list[float]:
    """Get embedding via OpenRouter."""
    payload = json.dumps({
        "model": EMBED_MODEL,
        "input": text[:8000]
    }).encode()
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    
    return data["data"][0]["embedding"]


def build_embed_text(entry: dict) -> str:
    """Build the text to embed — rich, searchable."""
    parts = [
        f"Position: {entry['position_name']}",
        f"Cluster: {entry['cluster_family']}",
        f"Mastery Definition: {entry['mastery_definition']}",
        f"Core Skills: {', '.join(entry['core_skills'])}",
        f"Common Failures: {'; '.join(entry['common_failures'])}",
        f"Formula Overlay: {entry['formula_overlay']}",
        f"Example Scenario: {entry['example_scenario']}"
    ]
    return "\n".join(parts)


def main():
    print(f"📌 Uploading mastery research to Pinecone")
    print(f"   Index: {INDEX_NAME}")
    print(f"   Namespace: {NAMESPACE}")
    print()
    
    # Load all JSON files
    files = sorted(RESEARCH_DIR.glob("*.json"))
    files = [f for f in files if f.name != "_summary.json" and not f.name.endswith("_RAW.txt")]
    
    print(f"   Found {len(files)} research files")
    
    vectors = []
    errors = []
    
    for i, fpath in enumerate(files, 1):
        try:
            with open(fpath) as f:
                entry = json.load(f)
            
            position = entry["position_name"]
            cluster = entry["cluster_family"]
            
            # Build embedding text
            embed_text = build_embed_text(entry)
            
            # Get embedding
            print(f"  [{i}/{len(files)}] Embedding: {position}...", end=" ", flush=True)
            embedding = get_embedding(embed_text)
            
            # Build vector
            vec_id = f"mastery_{fpath.stem}"
            
            # Pinecone metadata — flatten for searchability
            metadata = {
                "category": "position_mastery",
                "cluster_family": cluster,
                "position_name": position,
                "mastery_definition": entry["mastery_definition"][:500],
                "core_skills": ", ".join(entry["core_skills"]),
                "textbooks": ", ".join(entry.get("textbooks_references", [])),
                "best_practices": ", ".join(entry.get("best_practices", [])),
                "tools_platforms": ", ".join(entry.get("tools_platforms", [])),
                "common_failures": "; ".join(entry["common_failures"])[:500],
                "formula_overlay": entry["formula_overlay"][:500],
                "example_scenario": entry["example_scenario"][:500],
                "source": f"mastery-research/{fpath.name}",
                "date": "2026-03-07"
            }
            
            vectors.append({
                "id": vec_id,
                "values": embedding,
                "metadata": metadata
            })
            
            print("✅")
            
            # Rate limit: ~3 per second for embeddings
            if i % 3 == 0:
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            errors.append({"file": fpath.name, "error": str(e)})
    
    print(f"\n   Embedded {len(vectors)} vectors. Uploading to Pinecone...")
    
    # Upload in batches of 20
    batch_size = 20
    uploaded = 0
    for batch_start in range(0, len(vectors), batch_size):
        batch = vectors[batch_start:batch_start + batch_size]
        index.upsert(
            vectors=[(v["id"], v["values"], v["metadata"]) for v in batch],
            namespace=NAMESPACE
        )
        uploaded += len(batch)
        print(f"   Uploaded batch: {uploaded}/{len(vectors)}")
    
    print(f"\n{'='*60}")
    print(f"🏁 COMPLETE")
    print(f"   ✅ Uploaded: {uploaded}")
    print(f"   ❌ Errors: {len(errors)}")
    
    if errors:
        print(f"\n   Failed files:")
        for e in errors:
            print(f"     - {e['file']}: {e['error']}")
    
    # Verify
    stats = index.describe_index_stats()
    ns_stats = stats.get("namespaces", {}).get(NAMESPACE, {})
    print(f"\n   Namespace '{NAMESPACE}' now has {ns_stats.get('vector_count', '?')} vectors")


if __name__ == "__main__":
    main()
