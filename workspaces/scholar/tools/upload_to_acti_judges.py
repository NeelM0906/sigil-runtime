#!/usr/bin/env python3
"""
Upload mastery profiles to acti-judges Pinecone index
One namespace per cluster (e.g. namespace="hunter", namespace="oracle")
Format: splits mastery profile into sections, uploads each section as a separate vector

Usage: python3 upload_to_acti_judges.py [--cluster hunter] [--all]
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

WORKSPACE = Path("~/.openclaw/workspace-forge")
MASTERY_DIR = WORKSPACE / "reports" / "mastery-database"

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
PINECONE_INDEX_HOST = "https://acti-judges-hw65sks.svc.aped-4627-b74a.pinecone.io"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536


def get_embedding(text: str) -> list:
    """Get embedding via OpenRouter proxy."""
    url = "https://openrouter.ai/api/v1/embeddings"
    payload = json.dumps({
        "model": EMBED_MODEL,
        "input": text[:8000]  # truncate if needed
    }).encode()
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
        return data["data"][0]["embedding"]


def upsert_vectors(vectors: list, namespace: str):
    """Upsert vectors to acti-judges Pinecone index."""
    url = f"{PINECONE_INDEX_HOST}/vectors/upsert"
    payload = json.dumps({
        "vectors": vectors,
        "namespace": namespace
    }).encode()
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Api-Key": PINECONE_API_KEY,
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def split_into_sections(mastery_text: str) -> list:
    """Split mastery profile into 8 named sections."""
    section_patterns = [
        "DOMAIN DEFINITION",
        "CORE COMPETENCIES",
        "TECHNICAL KNOWLEDGE",
        "MASTERY INDICATORS",
        "COMMON FAILURE PATTERNS",
        "LEARNING PATH",
        "SEAN CALLAGY FORMULA INTEGRATION",
        "REAL-WORLD SCENARIOS"
    ]
    
    sections = []
    lines = mastery_text.split('\n')
    current_section = "OVERVIEW"
    current_lines = []
    
    for line in lines:
        found_section = None
        for pattern in section_patterns:
            if pattern.lower() in line.lower() and len(line.strip()) < 100:
                found_section = pattern
                break
        
        if found_section:
            if current_lines:
                text = '\n'.join(current_lines).strip()
                if len(text) > 50:
                    sections.append((current_section, text))
            current_section = found_section
            current_lines = [line]
        else:
            current_lines.append(line)
    
    # Add last section
    if current_lines:
        text = '\n'.join(current_lines).strip()
        if len(text) > 50:
            sections.append((current_section, text))
    
    return sections


def upload_cluster(cluster_name: str) -> int:
    """Upload one cluster's mastery profile to acti-judges."""
    filepath = MASTERY_DIR / f"{cluster_name.lower()}-mastery.json"
    
    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return 0
    
    with open(filepath) as f:
        profile = json.load(f)
    
    namespace = cluster_name.lower()
    sections = split_into_sections(profile["mastery_profile"])
    
    if not sections:
        print(f"  ❌ No sections parsed for {cluster_name}")
        return 0
    
    vectors = []
    for i, (section_name, section_text) in enumerate(sections):
        # Full context for embedding
        embed_text = (
            f"CLUSTER: {profile['cluster']}\n"
            f"DOMAIN: {profile['domain']}\n"
            f"FAMILY: {profile['family']}\n"
            f"SECTION: {section_name}\n\n"
            f"{section_text}"
        )
        
        try:
            embedding = get_embedding(embed_text)
        except Exception as e:
            print(f"  ❌ Embedding failed for {cluster_name}/{section_name}: {e}")
            continue
        
        vector_id = f"{cluster_name.lower()}-{i+1:02d}-{section_name.lower().replace(' ', '-')[:20]}"
        
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "cluster": profile["cluster"],
                "domain": profile["domain"],
                "family": profile["family"],
                "positions": profile["positions"],
                "lever": profile["lever"],
                "section": section_name,
                "text": section_text[:1000],  # store first 1000 chars
                "uploaded_at": datetime.now().isoformat()
            }
        })
        
        time.sleep(0.5)  # rate limit
    
    if not vectors:
        return 0
    
    # Upsert in batches of 10
    batch_size = 10
    total_uploaded = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        try:
            result = upsert_vectors(batch, namespace)
            total_uploaded += len(batch)
        except Exception as e:
            print(f"  ❌ Upsert failed for batch {i}: {e}")
    
    return total_uploaded


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", help="Single cluster name")
    parser.add_argument("--all", action="store_true", help="Upload all completed clusters")
    parser.add_argument("--limit", type=int, default=80, help="Max clusters to upload")
    args = parser.parse_args()
    
    if not PINECONE_API_KEY or not OPENROUTER_API_KEY:
        print("ERROR: Missing PINECONE_API_KEY or OPENROUTER_API_KEY")
        sys.exit(1)
    
    if args.cluster:
        clusters = [args.cluster]
    else:
        # Get all completed clusters from disk
        files = list(MASTERY_DIR.glob("*-mastery.json"))
        clusters = [f.stem.replace("-mastery", "") for f in files]
        clusters = clusters[:args.limit]
    
    print(f"📤 Uploading {len(clusters)} clusters to acti-judges...")
    
    total_vectors = 0
    completed = 0
    
    for cluster_name in clusters:
        print(f"\n[{completed+1}/{len(clusters)}] {cluster_name}")
        count = upload_cluster(cluster_name)
        if count > 0:
            print(f"  ✅ {count} vectors uploaded → namespace:{cluster_name.lower()}")
            total_vectors += count
            completed += 1
        time.sleep(1)
    
    print(f"\n{'='*50}")
    print(f"✅ {completed}/{len(clusters)} clusters uploaded")
    print(f"📊 Total vectors in acti-judges: {total_vectors}")
    
    # Log to Supabase
    try:
        from supabase_memory import SaiMemory
        mem = SaiMemory("forge")
        mem.remember(
            "mastery_research",
            f"acti-judges UPLOAD COMPLETE: {completed} clusters, {total_vectors} vectors. Namespace per cluster. Ready for judge queries.",
            "upload_to_acti_judges.py",
            importance=9
        )
    except:
        pass


if __name__ == "__main__":
    main()
