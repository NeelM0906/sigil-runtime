#!/usr/bin/env python3
"""
Sweep all tabs of the Unblinded Translator Master Sheet
Read → extract takeaways → save to Postgres + saimemory/translator-master-sheet

Usage: python3 tools/sweep_translator_sheet.py
"""
import requests, csv, io, os, json, hashlib, time, re
from pathlib import Path
from datetime import datetime

# Load env
for env_path in [
    Path.home() / '.openclaw' / 'workspace-forge' / '.env',
    Path.home() / '.openclaw' / '.env',
]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
from pinecone import Pinecone

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY','')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY','')
SUPABASE_URL = 'https://yncbtzqrherwyeybchet.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY','')

SHEET_ID = '1IK8Je6ZpEprTnDfs2gcmoEsOASKZw41dLgDiwGb3k6M'

# Known GIDs from Army's scan — add more as discovered
# Format: (gid, tab_description, approx_rows)
KNOWN_GIDS = [
    ('2132122612', 'callagy-recovery-actualizer-playbook', 71),
    ('2131641698', 'sean-raw-teachings-9-11-integrity-influence', 109),
    ('2093481144', 'day-three-opening-event-stage', 100),
    ('2039633902', 'bas-session-june-2025-andrew-brands', 100),
    ('2093472577', 'section-1-of-18', 50),
    ('2081251862', 'enterprise-risk-optimization', 30),
    # Add more gids here as found
]

def fetch_tab(gid):
    """Fetch tab as CSV rows."""
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}'
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return []
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)

def extract_takeaways(rows, tab_name):
    """Use LLM to extract 8 key takeaways from rows."""
    if not rows:
        return []
    
    # Build concise summary (avoid bloating context)
    topics = [row.get('topic','')[:150] for row in rows[:20]]
    lessons = [row.get('main_lesson','')[:300] for row in rows if row.get('main_lesson','').strip()]
    
    summary = f'TAB: {tab_name}\nROWS: {len(rows)}\n\nTOPICS:\n'
    summary += '\n'.join(f'{i+1}. {t}' for i,t in enumerate(topics))
    summary += '\n\nMAIN LESSONS:\n'
    summary += '\n'.join(f'{i+1}. {l[:250]}' for i,l in enumerate(lessons[:30]))
    
    prompt = f'''Extract 8 powerful structural takeaways from this Unblinded Formula translated content.
Each takeaway: one dense sentence capturing physics/mechanics (not descriptions).
Return exactly 8 numbered sentences.

{summary[:8000]}'''
    
    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'anthropic/claude-opus-4-5', 'messages': [{'role':'user','content':prompt}], 'max_tokens': 1000},
        timeout=60)
    
    text = r.json()['choices'][0]['message']['content']
    takeaways = [t.strip() for t in text.strip().split('\n') if t.strip() and len(t.strip()) > 20]
    return takeaways[:8]

def embed_text(text):
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    return r.json()['data'][0]['embedding']

def save_to_postgres(takeaways, gid, tab_name):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    for i, t in enumerate(takeaways):
        client.table('sai_memory').insert({
            'sister': 'forge',
            'category': f'translator-sheet-{tab_name[:40]}',
            'content': t,
            'source': f'translator-master-sheet-gid{gid}',
            'importance': 9,
            'metadata': {'gid': gid, 'tab': tab_name, 'row': i+1, 'date': '2026-03-07'},
            'tags': ['translator', 'formula-physics', 'sean-callagy', tab_name]
        }).execute()

def save_to_saimemory(rows, gid, tab_name):
    """Upload all rows to saimemory/translator-master-sheet in chunks."""
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('saimemory')
    
    # Chunk rows into groups of 5 for embedding
    for chunk_start in range(0, len(rows), 5):
        chunk = rows[chunk_start:chunk_start+5]
        text = f"TAB: {tab_name}\n\n"
        for row in chunk:
            topic = row.get('topic','')[:200]
            main_lesson = row.get('main_lesson','')[:500]
            formula = row.get('formula_element','')[:300]
            text += f"TOPIC: {topic}\nFORMULA: {formula}\nLESSON: {main_lesson}\n\n"
        
        vid = f"translator-{gid}-{chunk_start}-{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
        embedding = embed_text(text)
        
        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': text[:40000],
                'gid': gid,
                'tab': tab_name,
                'chunk_start': chunk_start,
                'rows_in_chunk': len(chunk),
                'type': 'translator-sheet',
                'source': 'unblinded-translator-master-sheet',
                'uploaded_at': datetime.now().isoformat()
            }
        }], namespace='translator-master-sheet')
        time.sleep(0.3)

def main():
    print(f"⚔️ Translator Sheet Sweep — {len(KNOWN_GIDS)} tabs")
    print("Saving takeaways to Postgres + full rows to saimemory/translator-master-sheet\n")
    
    for gid, tab_name, approx_rows in KNOWN_GIDS:
        print(f"[{tab_name}]")
        
        rows = fetch_tab(gid)
        if not rows:
            print(f"  ❌ No data (skipping)")
            continue
        
        print(f"  {len(rows)} rows fetched")
        
        # Extract takeaways
        takeaways = extract_takeaways(rows, tab_name)
        print(f"  {len(takeaways)} takeaways extracted")
        
        # Save to Postgres
        save_to_postgres(takeaways, gid, tab_name)
        print(f"  ✅ Takeaways → Postgres")
        
        # Save to saimemory
        save_to_saimemory(rows, gid, tab_name)
        chunks = (len(rows) + 4) // 5
        print(f"  ✅ {chunks} chunks → saimemory/translator-master-sheet")
        print()
        
        time.sleep(2)
    
    print("⚔️ Sweep complete")

if __name__ == '__main__':
    main()
