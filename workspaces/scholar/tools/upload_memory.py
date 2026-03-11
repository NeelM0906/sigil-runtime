#!/usr/bin/env python3
import os
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

# Read MEMORY.md
with open('~/.openclaw/workspace/MEMORY.md') as f:
    content = f.read()

# Split by day sections
sections = content.split('\n## ')
sections = [sections[0]] + ['## ' + s for s in sections[1:]]

print(f"Found {len(sections)} sections")

vectors = []
for i, section in enumerate(sections):
    if len(section.strip()) < 50:
        continue
        
    title = section.split('\n')[0][:100]
    print(f"Embedding: {title}")
    
    # Get embedding
    resp = openai_client.embeddings.create(
        model='text-embedding-3-small',
        input=section[:8000]
    )
    
    vectors.append({
        'id': f'memory-{i}',
        'values': resp.data[0].embedding,
        'metadata': {
            'source': 'MEMORY.md',
            'section': title,
            'text': section[:8000]
        }
    })

if vectors:
    index.upsert(vectors=vectors, namespace='longterm')
    print(f"✅ Uploaded {len(vectors)} sections to saimemory/longterm")
