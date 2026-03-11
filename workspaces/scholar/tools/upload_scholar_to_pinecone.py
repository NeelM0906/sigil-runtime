#!/usr/bin/env python3
import os, glob, json, pathlib
from pinecone import Pinecone
from openai import OpenAI

def load_env():
    for env_path in [
        '~/.openclaw/workspace-forge/.env',
        '~/.openclaw/.env',
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        k, v = line.strip().split('=', 1)
                        os.environ.setdefault(k, v)

load_env()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not PINECONE_API_KEY:
    raise SystemExit('Missing PINECONE_API_KEY')

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index('saimemory')

# Embeddings via OpenRouter when present
openai_client = OpenAI(
    api_key=OPENROUTER_API_KEY or OPENAI_API_KEY,
    base_url='https://openrouter.ai/api/v1' if OPENROUTER_API_KEY else None,
)
EMBED_MODEL = 'openai/text-embedding-3-small' if OPENROUTER_API_KEY else 'text-embedding-3-small'

SRC_DIR = '~/.openclaw/workspace-scholar/memory'
# Upload only these scholar-owned files (avoid blasting everything)
patterns = [
    'judge-audit-2026-02-28.md',
    'scholar-elite-training-adam-athena-dr-nate-feb28.md',
    'sean-message-scoreboards-takeaways-2026-02-28.md',
    'sean-message-methodology-scoreboards-2026-02-28.txt',
    'data-providers-comparison-za8-2026-02-28.md',
    'zone-action-roadmap-sop-2026-02-28.md',
    'COORDINATION-README.md',
    '2026-02-28.md',
]

files = []
for p in patterns:
    fp = os.path.join(SRC_DIR, p)
    if os.path.exists(fp):
        files.append(fp)

print(f'Found {len(files)} files to upload')

namespace = 'scholar'

uploaded = 0
for filepath in files:
    filename = os.path.basename(filepath)
    text = pathlib.Path(filepath).read_text(errors='ignore')
    # split into sections (##) to keep vectors smaller
    sections = text.split('\n## ')
    sections = [sections[0]] + ['## ' + s for s in sections[1:]]

    vectors=[]
    for i, section in enumerate(sections):
        s = section.strip()
        if len(s) < 120:
            continue
        title = s.split('\n',1)[0][:120]
        inp = s[:8000]
        resp = openai_client.embeddings.create(model=EMBED_MODEL, input=inp)
        vec = {
            'id': f'scholar-{filename}-{i}',
            'values': resp.data[0].embedding,
            'metadata': {
                'source': f'scholar:{filename}',
                'section': title,
                'text': inp,
                'path': filepath,
                'owner': 'scholar',
                'date': '2026-02-28',
            }
        }
        vectors.append(vec)

    if vectors:
        index.upsert(vectors=vectors, namespace=namespace)
        uploaded += len(vectors)
        print(f'✅ {filename}: {len(vectors)} vectors')

print(f'🎉 Uploaded total vectors: {uploaded} to saimemory/{namespace}')
