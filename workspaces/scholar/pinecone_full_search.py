import os, sys, json
os.environ['PINECONE_API_KEY'] = 'pcsk_4Eksyx_5CVWnPFdnSG7aVUawiq5XshFogV1yEgP27nehyBAnog9jiHJQRucSY9rtrErFVT'

envdata = open('/Users/zidane/Downloads/PROJEKT/.env').read()
for line in envdata.split('\n'):
    if line.startswith('OPENAI_API_KEY='):
        os.environ['OPENAI_API_KEY'] = line.split('=',1)[1].strip()

from pinecone import Pinecone
from openai import OpenAI
pc = Pinecone()
oai = OpenAI()

def embed(text):
    r = oai.embeddings.create(input=text, model="text-embedding-ada-002")
    return r.data[0].embedding

queries = [
    "Unblinded Formula 4 Steps of Influence",
    "7 Destroyers Self Mastery Liberators",
    "12 Indispensable Elements emotional rapport",
    "Process Mastery 7 Levers marketing sales",
    "4 Energies Fun Aspirational Goddess Zeus",
]

idx_name = sys.argv[1]
print(f"\n{'='*60}")
print(f"INDEX: {idx_name}")
print(f"{'='*60}")

idx = pc.Index(idx_name)

for q in queries:
    vec = embed(q)
    results = idx.query(vector=vec, top_k=2, include_metadata=True)
    best = results.matches[0] if results.matches else None
    if best:
        meta = best.metadata or {}
        text = meta.get('text', meta.get('content', meta.get('chunk_text', meta.get('page_content', str(meta)[:300]))))
        print(f"\nQ: {q}")
        print(f"  Best Score: {best.score:.4f}")
        print(f"  Text: {str(text)[:300]}")
