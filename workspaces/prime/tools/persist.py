#!/usr/bin/env python3
"""
persist.py — Shared persistence for all SAI sisters.
One command → Postgres + Pinecone. No excuses.

Usage:
  python3 persist.py --title "Kai Training S11 — 9.5 Godzilla" \
                     --content "Full description here..." \
                     --category kai_training \
                     --source sai \
                     --importance 10 \
                     --date 2026-03-10

  # Or pipe content from stdin:
  echo "Content here" | python3 persist.py --title "..." --source forge --category deliverable

  # Batch from JSON file:
  python3 persist.py --batch entries.json

Categories: kai_training, deliverable, sean_directive, directive, technical, system,
            ip_filing, foundational, mission, principle, decision, zone_action, session_summary

Sources: sai, forge, scholar, recovery, memory, sean, aiko, adam, kai, system

Importance: 1-10 (default 7)
"""

import os
import sys
import json
import uuid
import argparse
import requests
from datetime import datetime, timezone

# ─── Config ───
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_INDEX = 'saimemory'
PINECONE_NAMESPACE = 'longterm'
EMBED_MODEL = 'openai/text-embedding-3-small'

VALID_SOURCES = ['sai', 'forge', 'scholar', 'recovery', 'memory', 'sean', 'aiko', 'adam', 'kai', 'system', 'prime']
VALID_CATEGORIES = [
    'kai_training', 'deliverable', 'sean_directive', 'directive', 'technical',
    'system', 'ip_filing', 'foundational', 'mission', 'principle', 'decision',
    'zone_action', 'session_summary', 'research', 'identity', 'plan',
    'learning', 'contact', 'meeting', 'recovery_medical'
]


def embed_texts(texts):
    """Embed via OpenRouter."""
    r = requests.post(
        'https://openrouter.ai/api/v1/embeddings',
        headers={
            'Authorization': f'Bearer {OPENROUTER_KEY}',
            'Content-Type': 'application/json'
        },
        json={'model': EMBED_MODEL, 'input': texts},
        timeout=30
    )
    r.raise_for_status()
    return [d['embedding'] for d in r.json()['data']]


def write_postgres(entries):
    """Write entries to Supabase sai_memory table."""
    url = f"{SUPABASE_URL}/rest/v1/sai_memory"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    rows = []
    for e in entries:
        rows.append({
            'id': e.get('id', str(uuid.uuid4())),
            'content': e['content'],
            'category': e.get('category', 'deliverable'),
            'source': e.get('source', 'system'),
            'importance': e.get('importance', 7),
            'session_date': e.get('date', datetime.now().strftime('%Y-%m-%d')),
            'title': e.get('title', None),
        })
    
    # Batch in groups of 10
    written = 0
    for i in range(0, len(rows), 10):
        batch = rows[i:i+10]
        r = requests.post(url, headers=headers, json=batch, timeout=15)
        if r.status_code in (200, 201):
            written += len(batch)
        else:
            print(f"⚠️ Postgres batch {i//10+1} failed: {r.status_code} — {r.text[:200]}", file=sys.stderr)
    
    return written


def write_pinecone(entries):
    """Write entries to Pinecone saimemory index."""
    from pinecone import Pinecone
    
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(PINECONE_INDEX)
    
    texts = [e['content'] for e in entries]
    embeddings = embed_texts(texts)
    
    vectors = []
    for i, e in enumerate(entries):
        vid = e.get('pinecone_id', f"{e.get('source','sai')}-{e.get('id', str(uuid.uuid4())[:8])}")
        meta = {
            'text': e['content'],
            'category': e.get('category', 'deliverable'),
            'source': e.get('source', 'system'),
            'date': e.get('date', datetime.now().strftime('%Y-%m-%d')),
        }
        if e.get('title'):
            meta['title'] = e['title']
        vectors.append({'id': vid, 'values': embeddings[i], 'metadata': meta})
    
    index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)
    return len(vectors)


def persist(entries, skip_postgres=False, skip_pinecone=False, dry_run=False):
    """Persist entries to both stores."""
    if not entries:
        print("Nothing to persist.")
        return
    
    if dry_run:
        print(f"🔍 DRY RUN — {len(entries)} entries:")
        for e in entries:
            print(f"  [{e.get('source','?')}] [{e.get('category','?')}] {e.get('title', e['content'][:60])}")
        return
    
    pg_count = 0
    pc_count = 0
    
    if not skip_postgres:
        try:
            pg_count = write_postgres(entries)
            print(f"✅ Postgres: {pg_count}/{len(entries)} entries written")
        except Exception as ex:
            print(f"❌ Postgres failed: {ex}", file=sys.stderr)
    
    if not skip_pinecone:
        try:
            pc_count = write_pinecone(entries)
            print(f"✅ Pinecone: {pc_count}/{len(entries)} vectors upserted")
        except Exception as ex:
            print(f"❌ Pinecone failed: {ex}", file=sys.stderr)
    
    print(f"\n🔥 Persisted {len(entries)} entries — PG:{pg_count} PC:{pc_count}")


def main():
    parser = argparse.ArgumentParser(description='Persist to Postgres + Pinecone')
    parser.add_argument('--title', '-t', help='Entry title')
    parser.add_argument('--content', '-c', help='Entry content (or pipe via stdin)')
    parser.add_argument('--category', '-g', default='deliverable', help=f'Category: {", ".join(VALID_CATEGORIES)}')
    parser.add_argument('--source', '-s', default='sai', help=f'Source: {", ".join(VALID_SOURCES)}')
    parser.add_argument('--importance', '-i', type=int, default=7, help='Importance 1-10')
    parser.add_argument('--date', '-d', default=datetime.now().strftime('%Y-%m-%d'), help='Session date YYYY-MM-DD')
    parser.add_argument('--pinecone-id', '-p', help='Custom Pinecone vector ID')
    parser.add_argument('--batch', '-b', help='JSON file with array of entries')
    parser.add_argument('--skip-postgres', action='store_true', help='Skip Postgres write')
    parser.add_argument('--skip-pinecone', action='store_true', help='Skip Pinecone write')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be persisted')
    
    args = parser.parse_args()
    
    entries = []
    
    if args.batch:
        with open(args.batch, 'r') as f:
            entries = json.load(f)
    else:
        content = args.content
        if not content and not sys.stdin.isatty():
            content = sys.stdin.read().strip()
        
        if not content:
            print("Error: --content required (or pipe via stdin)", file=sys.stderr)
            sys.exit(1)
        
        entry = {
            'id': str(uuid.uuid4()),
            'title': args.title,
            'content': content,
            'category': args.category,
            'source': args.source,
            'importance': args.importance,
            'date': args.date,
        }
        if args.pinecone_id:
            entry['pinecone_id'] = args.pinecone_id
        
        entries = [entry]
    
    # Validate
    for e in entries:
        if e.get('source') and e['source'] not in VALID_SOURCES:
            print(f"⚠️ Unknown source '{e['source']}' — valid: {', '.join(VALID_SOURCES)}", file=sys.stderr)
        if e.get('category') and e['category'] not in VALID_CATEGORIES:
            print(f"⚠️ Unknown category '{e['category']}' — valid: {', '.join(VALID_CATEGORIES)}", file=sys.stderr)
    
    persist(entries, skip_postgres=args.skip_postgres, skip_pinecone=args.skip_pinecone, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
