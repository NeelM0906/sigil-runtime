#!/usr/bin/env python3
"""Query Sai's long-term memory from Pinecone"""
import sys
import os

# Load env
with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from pinecone import Pinecone
from openai import OpenAI

pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
index = pc.Index('saimemory')

query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
namespace = 'daily'  # or 'longterm'
top_k = 5

emb = openai.embeddings.create(model='text-embedding-3-small', input=query).data[0].embedding
results = index.query(vector=emb, top_k=top_k, include_metadata=True, namespace=namespace)

print(f"\n🔍 Query: {query}\n")
for i, r in enumerate(results.matches, 1):
    print(f"[{i}] {r.metadata.get('source', 'unknown')} (score: {r.score:.3f})")
    print(f"    Section: {r.metadata.get('section', 'N/A')[:80]}")
    print(f"    {r.metadata.get('text', '')[:300]}...")
    print()
