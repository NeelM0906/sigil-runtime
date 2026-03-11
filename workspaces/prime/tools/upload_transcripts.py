#!/usr/bin/env python3
"""Upload verbatim Sean transcripts to Pinecone saimemory.

Each transcript is chunked into ~500-word segments with overlap,
tagged with date, speaker, topic, and source file.

Usage:
    python3 upload_transcripts.py                    # Upload all
    python3 upload_transcripts.py --file <path>      # Upload one
    python3 upload_transcripts.py --dry-run           # Preview chunks
"""

import os, sys, re, json, hashlib, time, glob
from pathlib import Path

# Add workspace tools to path
sys.path.insert(0, os.path.dirname(__file__))

WORKSPACE = os.path.join(os.environ["HOME"], ".openclaw", "workspace")
TRANSCRIPTS_DIR = os.path.join(WORKSPACE, "memory", "transcripts")
NAMESPACE = "sean-transcripts-verbatim"

CHUNK_SIZE = 500  # words
CHUNK_OVERLAP = 75  # words overlap between chunks


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break
    return chunks


def extract_metadata(filepath):
    """Extract date, speakers, topic from filename and content."""
    fname = os.path.basename(filepath)
    
    # Parse date from filename: 2026-03-05_sean_colosseum_vision.md
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    date = date_match.group(1) if date_match else "unknown"
    
    # Parse topic from filename
    topic_part = fname.replace(".md", "").replace(".pdf", "")
    if date_match:
        topic_part = topic_part[len(date_match.group(0)):].strip("_- ")
    topic = topic_part.replace("_", " ").replace("-", " ").title()
    
    # Read first few lines for speaker detection
    with open(filepath, "r") as f:
        header = f.read(500).lower()
    
    speakers = []
    for name in ["sean", "adam", "aiko", "mark", "nick", "nadav", "joey"]:
        if name in header:
            speakers.append(name)
    if not speakers:
        speakers = ["sean"]  # default
    
    return {
        "date": date,
        "topic": topic,
        "speakers": ", ".join(speakers),
        "source_file": os.path.relpath(filepath, WORKSPACE),
    }


def get_embedding(text, api_key):
    """Get embedding via OpenRouter."""
    import urllib.request
    
    data = json.dumps({
        "input": text[:8000],  # Truncate for embedding
        "model": "openai/text-embedding-3-small",
    }).encode()
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/embeddings",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    return result["data"][0]["embedding"]


def upload_to_pinecone(vectors, api_key):
    """Batch upload vectors to Pinecone saimemory."""
    from pinecone import Pinecone
    
    pc = Pinecone(api_key=api_key)
    idx = pc.Index("saimemory")
    
    # Upload in batches of 50
    batch_size = 50
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        idx.upsert(vectors=batch, namespace=NAMESPACE)
        print(f"  Uploaded batch {i // batch_size + 1} ({len(batch)} vectors)")
        time.sleep(0.5)
    
    return len(vectors)


def process_transcript(filepath, openrouter_key, pinecone_key, dry_run=False):
    """Process one transcript file."""
    print(f"\n📄 Processing: {os.path.basename(filepath)}")
    
    with open(filepath, "r") as f:
        content = f.read()
    
    if len(content.strip()) < 100:
        print("  ⚠️ Too short, skipping")
        return 0
    
    meta = extract_metadata(filepath)
    print(f"  Date: {meta['date']} | Topic: {meta['topic']} | Speakers: {meta['speakers']}")
    
    chunks = chunk_text(content)
    print(f"  Chunks: {len(chunks)}")
    
    if dry_run:
        for i, chunk in enumerate(chunks[:3]):
            print(f"  --- Chunk {i + 1} ({len(chunk.split())} words) ---")
            print(f"  {chunk[:200]}...")
        if len(chunks) > 3:
            print(f"  ... and {len(chunks) - 3} more chunks")
        return len(chunks)
    
    vectors = []
    for i, chunk in enumerate(chunks):
        # Create unique ID from content hash
        chunk_id = hashlib.md5(f"{filepath}:{i}:{chunk[:100]}".encode()).hexdigest()
        
        # Get embedding
        embedding = get_embedding(chunk, openrouter_key)
        
        vectors.append({
            "id": f"transcript-{chunk_id}",
            "values": embedding,
            "metadata": {
                "text": chunk,
                "content": chunk,
                "date": meta["date"],
                "topic": meta["topic"],
                "speakers": meta["speakers"],
                "source_file": meta["source_file"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "type": "verbatim-transcript",
            },
        })
        
        if (i + 1) % 10 == 0:
            print(f"  Embedded {i + 1}/{len(chunks)} chunks")
        time.sleep(0.2)  # Rate limiting
    
    # Upload
    count = upload_to_pinecone(vectors, pinecone_key)
    print(f"  ✅ Uploaded {count} vectors to saimemory/{NAMESPACE}")
    return count


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload transcripts to Pinecone")
    parser.add_argument("--file", help="Upload a specific file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--pattern", default="*sean*", help="Glob pattern for transcript files")
    args = parser.parse_args()
    
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    pinecone_key = os.environ.get("PINECONE_API_KEY")
    
    if not args.dry_run:
        if not openrouter_key:
            print("❌ OPENROUTER_API_KEY not set")
            sys.exit(1)
        if not pinecone_key:
            print("❌ PINECONE_API_KEY not set")
            sys.exit(1)
    
    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, f"{args.pattern}.md")))
    
    if not files:
        print("No transcript files found")
        sys.exit(1)
    
    print(f"Found {len(files)} transcript(s)")
    total = 0
    
    for f in files:
        count = process_transcript(f, openrouter_key, pinecone_key, dry_run=args.dry_run)
        total += count
    
    print(f"\n🔥 Total: {total} vectors {'(dry run)' if args.dry_run else 'uploaded'}")


if __name__ == "__main__":
    main()
