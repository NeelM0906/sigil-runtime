#!/usr/bin/env python3
"""Upload judge specs, strata mines, being specs, and D7 skill judges to acti-judges Pinecone index."""

import os, sys, hashlib, time, re
from pathlib import Path

# Add tools dir to path
sys.path.insert(0, str(Path(__file__).parent))

from pinecone import Pinecone
import requests

WORKSPACE = Path(__file__).parent.parent
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
INDEX_NAME = "acti-judges"
EMBED_MODEL = "text-embedding-3-small"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
CHUNK_SIZE = 1500  # chars per chunk
CHUNK_OVERLAP = 200

pc = Pinecone(api_key=PINECONE_API_KEY)
idx = pc.Index(INDEX_NAME)


def get_embedding(text: str) -> list[float]:
    """Get embedding via OpenRouter."""
    resp = requests.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": f"openai/{EMBED_MODEL}", "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks at paragraph boundaries."""
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current = ""
    
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of current chunk
            words = current.split()
            overlap_words = words[-min(len(words), overlap // 5):]
            current = " ".join(overlap_words) + "\n\n" + para
        else:
            current = current + "\n\n" + para if current else para
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks


def upload_file(filepath: str, namespace: str, metadata_extra: dict = None):
    """Upload a file to acti-judges in chunks."""
    path = Path(filepath)
    if not path.exists():
        print(f"  SKIP (not found): {filepath}")
        return 0
    
    text = path.read_text()
    chunks = chunk_text(text)
    
    vectors = []
    for i, chunk in enumerate(chunks):
        vec_id = hashlib.md5(f"{namespace}:{path.name}:{i}".encode()).hexdigest()
        embedding = get_embedding(chunk)
        
        meta = {
            "text": chunk[:4000],  # Pinecone metadata limit
            "source": str(path.relative_to(WORKSPACE)),
            "chunk": i,
            "total_chunks": len(chunks),
        }
        if metadata_extra:
            meta.update(metadata_extra)
        
        vectors.append({"id": vec_id, "values": embedding, "metadata": meta})
        
        # Batch upsert every 20 vectors
        if len(vectors) >= 20:
            idx.upsert(vectors=vectors, namespace=namespace)
            vectors = []
            time.sleep(0.2)
    
    # Final batch
    if vectors:
        idx.upsert(vectors=vectors, namespace=namespace)
    
    print(f"  ✅ {namespace}: {len(chunks)} vectors from {path.name}")
    return len(chunks)


# Define all uploads: (filepath, namespace, extra_metadata)
UPLOADS = [
    # === CORE JUDGE FRAMEWORKS ===
    ("reports/formula-judge-v1.md", "formula-judge", {"layer": "universal", "type": "judge"}),
    ("reports/domain-judge-specs-complete.md", "domain-judge-specs", {"layer": "domain", "type": "judge"}),
    ("reports/kai-technical-judge-architecture.md", "judge-architecture", {"layer": "architecture", "type": "blueprint"}),
    
    # === STRATA MINING ROUND 1 ===
    ("reports/strata-mine-d1-d2.md", "strata-mine-d1d2", {"layer": "strata", "type": "benchmarks", "round": 1}),
    ("reports/strata-mine-d3-d4.md", "strata-mine-d3d4", {"layer": "strata", "type": "benchmarks", "round": 1}),
    ("reports/strata-mine-d5-d6.md", "strata-mine-d5d6", {"layer": "strata", "type": "benchmarks", "round": 1}),
    ("reports/strata-mine-d7-d8.md", "strata-mine-d7d8", {"layer": "strata", "type": "benchmarks", "round": 1}),
    
    # === STRATA MINING ROUND 2 ===
    ("reports/strata-mine-round2-d1d2.md", "strata-mine-r2-d1d2", {"layer": "strata", "type": "benchmarks", "round": 2}),
    ("reports/strata-mine-round2-d3d4d5.md", "strata-mine-r2-d3d4d5", {"layer": "strata", "type": "benchmarks", "round": 2}),
    ("reports/strata-mine-round2-d6d7.md", "strata-mine-r2-d6d7", {"layer": "strata", "type": "benchmarks", "round": 2}),
    ("reports/strata-mine-round2-d8.md", "strata-mine-r2-d8", {"layer": "strata", "type": "benchmarks", "round": 2}),
    
    # === BEING SPECS ===
    ("reports/writer-being-v1.md", "being-writer", {"layer": "being", "type": "being-spec"}),
    ("reports/writer-technical-judge-v1.md", "judge-writer-technical", {"layer": "cluster", "type": "judge"}),
    ("reports/strategist-being-v1.md", "being-strategist", {"layer": "being", "type": "being-spec"}),
    
    # === CALIBRATION ===
    ("reports/self-mastery-calibration-anchors.md", "self-mastery-calibration", {"layer": "calibration", "type": "anchors"}),
    ("reports/colosseum-v4-design-concept.md", "colosseum-v4-design", {"layer": "architecture", "type": "blueprint"}),
    
    # === D7 FINANCIAL & LEGAL SKILL JUDGES ===
    ("skills/judge-d7-financial-legal/SKILL.md", "judge-d7-domain", {"layer": "domain", "type": "judge", "domain": "D7-Financial-Legal"}),
    ("skills/judge-d7-financial-legal/clusters/sc1-revenue-operations.md", "judge-d7-sc1-revops", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC1"}),
    ("skills/judge-d7-financial-legal/clusters/sc2-tax-strategy.md", "judge-d7-sc2-tax", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC2"}),
    ("skills/judge-d7-financial-legal/clusters/sc3-recovery-operations.md", "judge-d7-sc3-recovery", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC3"}),
    ("skills/judge-d7-financial-legal/clusters/sc4-legal-review.md", "judge-d7-sc4-legal", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC4"}),
    ("skills/judge-d7-financial-legal/clusters/sc5-financial-planning.md", "judge-d7-sc5-finplan", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC5"}),
    ("skills/judge-d7-financial-legal/clusters/sc6-disposable-income-modeling.md", "judge-d7-sc6-disposable", {"layer": "cluster", "type": "judge", "domain": "D7", "cluster": "SC6"}),
]


def main():
    total = 0
    print(f"\n🔥 Uploading {len(UPLOADS)} files to acti-judges\n")
    
    for filepath, namespace, meta in UPLOADS:
        full_path = WORKSPACE / filepath
        count = upload_file(str(full_path), namespace, meta)
        total += count
        time.sleep(0.3)  # Rate limiting
    
    print(f"\n{'='*50}")
    print(f"🏛️  TOTAL: {total} vectors uploaded to acti-judges")
    print(f"📁 Files: {len(UPLOADS)}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
