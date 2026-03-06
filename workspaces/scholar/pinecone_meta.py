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

idx_name = sys.argv[1] if len(sys.argv) > 1 else 'ublib2'
idx = pc.Index(idx_name)

# Fetch a sample vector by ID from above results
sample_ids = ['255afc68-a12c-4c00-ba3c-7cd44a25c53a']
result = idx.fetch(ids=sample_ids)
for vid, vdata in result.vectors.items():
    print(f"ID: {vid}")
    meta = vdata.metadata
    print(f"Metadata keys: {list(meta.keys())}")
    for k, v in meta.items():
        print(f"  {k}: {str(v)[:200]}")
    print(f"Vector dim: {len(vdata.values)}")
