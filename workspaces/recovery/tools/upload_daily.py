#!/usr/bin/env python3
import os
import glob
from pinecone import Pinecone
from openai import OpenAI

# Load env
env_path = '~/.openclaw/workspace-forge/.env'
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

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
        
        resp = openai_client.embeddings.create(
            model='text-embedding-3-small',
            input=section[:8000]
        )
        
        vectors.append({
            'id': f'{filename}-{i}',
            'values': resp.data[0].embedding,
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
