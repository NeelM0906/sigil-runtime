#!/usr/bin/env python3
import os
import glob
from pinecone import Pinecone
import requests

OPENROUTER_EMBED_URL = "https://openrouter.ai/api/v1/embeddings"

# Load env
env_path = '~/.openclaw/workspace-forge/.env'
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])

# Embeddings MUST go via OpenRouter (per ecosystem rule). No OpenAI direct.
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise SystemExit("Missing OPENROUTER_API_KEY in env")

def embed(text: str):
    resp = requests.post(
        OPENROUTER_EMBED_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            # Optional headers help OpenRouter analytics/routing
            "HTTP-Referer": "https://acti.ai",
            "X-Title": "SAI upload_daily",
        },
        json={
            "model": "openai/text-embedding-3-small",
            "input": text,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    emb = data["data"][0]["embedding"]
    # Pinecone requires floats
    return [float(x) for x in emb]

index = pc.Index('saimemory')

# Get all daily memory files
memory_dir = '~/.openclaw/workspace/memory'
files = sorted(glob.glob(f'{memory_dir}/*.md'))

for filepath in files:
    filename = os.path.basename(filepath)
    with open(filepath) as f:
        content = f.read()
    
    # Split by ## sections
    sections = content.split('\n## ')
    sections = [sections[0]] + ['## ' + s for s in sections[1:]]
    
    print(f"\n📁 {filename}: {len(sections)} sections")
    
    vectors = []
    for i, section in enumerate(sections):
        if len(section.strip()) < 100:
            continue
        
        title = section.split('\n')[0][:100]
        print(f"  → {title[:60]}...")
        
        embedding = embed(section[:8000])

        vectors.append({
            'id': f'{filename}-{i}',
            'values': embedding,
            'metadata': {
                'source': filename,
                'section': title,
                'text': section[:8000]
            }
        })
    
    if vectors:
        index.upsert(vectors=vectors, namespace='daily')
        print(f"  ✅ Uploaded {len(vectors)} sections")

print("\n🎉 All daily memories uploaded!")
