import os, json
os.environ['PINECONE_API_KEY'] = 'pcsk_4Eksyx_5CVWnPFdnSG7aVUawiq5XshFogV1yEgP27nehyBAnog9jiHJQRucSY9rtrErFVT'
os.environ['OPENAI_API_KEY'] = open('/Users/zidane/Downloads/PROJEKT/.env').read().split('OPENAI_API_KEY=')[1].split('\n')[0]

from pinecone import Pinecone
from openai import OpenAI

pc = Pinecone()
oai = OpenAI()

def embed(text):
    r = oai.embeddings.create(input=text, model="text-embedding-ada-002")
    return r.data[0].embedding

queries = [
    "Unblinded Formula 4 Steps of Influence 7 Destroyers 12 Indispensable Elements",
    "Sean Callagy Self Mastery Influence Mastery Process Mastery three masteries",
    "7 Levers marketing sales process mastery ecosystem mergers",
    "4 Energies Fun Aspirational Goddess Zeus influence",
    "39 components Unblinded Results Formula Liberators",
]

indexes_to_search = [
    'ublib2', 'athenacontextualmemory', 'stratablue', 'saimemory',
    'seanmiracontextualmemory', 'adamathenacontextualmemory',
    'seancallieupdates', 'miracontextualmemory'
]

import sys
idx_name = sys.argv[1] if len(sys.argv) > 1 else 'ublib2'
print(f"\n=== SEARCHING: {idx_name} ===")
idx = pc.Index(idx_name)

for q in queries:
    vec = embed(q)
    try:
        results = idx.query(vector=vec, top_k=3, include_metadata=True)
        hits = results.matches
        if hits and hits[0].score > 0.75:
            print(f"\nQuery: {q[:60]}...")
            for h in hits:
                meta = h.metadata if h.metadata else {}
                text = meta.get('text', meta.get('content', meta.get('chunk_text', '')))[:300]
                print(f"  Score: {h.score:.4f} | ID: {h.id[:50]}")
                if text:
                    print(f"  Text: {text[:250]}...")
    except Exception as e:
        print(f"  Error: {e}")
