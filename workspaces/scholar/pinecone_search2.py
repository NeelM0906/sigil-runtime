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

query = "Unblinded Formula Sean Callagy 4 Steps Influence 7 Destroyers Self Mastery"
vec = embed(query)

idx_name = sys.argv[1] if len(sys.argv) > 1 else 'ublib2'
print(f"=== {idx_name} ===")
idx = pc.Index(idx_name)

results = idx.query(vector=vec, top_k=5, include_metadata=True)
for h in results.matches:
    meta = h.metadata if h.metadata else {}
    text = meta.get('text', meta.get('content', meta.get('chunk_text', meta.get('page_content', ''))))
    if not text:
        text = str(meta)[:400]
    print(f"\nScore: {h.score:.4f} | ID: {h.id[:60]}")
    print(f"Text: {str(text)[:350]}")
    print("---")
