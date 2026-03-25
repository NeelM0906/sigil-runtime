#!/usr/bin/env python3
"""
api_docs.py — Sai's API troubleshooting knowledge base.

Every API gotcha, working pattern, and battle-tested snippet goes here.
Stored in Pinecone saimemory/api-docs for instant semantic search.

Usage:
  # Log a working pattern
  python3 api_docs.py log --service fal.ai --title "Kling v3 polling" \
    --content "Use GET queue.fal.run/fal-ai/kling-video/requests/{id} — NOT POST. Poll every 5s." \
    --tags "kling,polling,video"

  # Log a gotcha / broken thing
  python3 api_docs.py gotcha --service fal.ai --title "frame-extraction doesn't exist" \
    --content "fal-ai/video-utils/frame-extraction returns 404. Use ffmpeg locally instead." \
    --tags "frames,video-utils"

  # Log a working code snippet
  python3 api_docs.py snippet --service elevenlabs --title "Upload knowledge base text" \
    --content "POST /v1/convai/knowledge-base/text {name, text} → returns {id}" \
    --tags "knowledge-base,convai"

  # Search for help
  python3 api_docs.py search "kling video polling 404"

  # List everything for a service
  python3 api_docs.py list --service fal.ai

  # Batch import from JSON
  python3 api_docs.py batch docs.json
"""

import os
import sys
import json
import hashlib
import argparse
import requests
from datetime import datetime, timezone

# ─── Load env ───
ENV_PATH = '/Users/samantha/.openclaw/workspace-forge/.env'
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_HOST = 'https://saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io'
EMBED_MODEL = 'openai/text-embedding-3-small'
NAMESPACE = 'api-docs'


def embed(text, retries=3):
    """Get embedding via OpenRouter with retry."""
    import time
    for attempt in range(retries):
        try:
            r = requests.post(
                'https://openrouter.ai/api/v1/embeddings',
                headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
                json={'model': EMBED_MODEL, 'input': [text]},
                timeout=60
            )
            r.raise_for_status()
            return r.json()['data'][0]['embedding']
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⏳ Timeout, retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                raise


def make_id(service, title):
    """Deterministic ID so re-logging the same thing updates it."""
    h = hashlib.md5(f'{service}:{title}'.lower().encode()).hexdigest()[:12]
    return f'api-{h}'


def upsert(id_, text, metadata):
    """Upsert to Pinecone."""
    vec = embed(text)
    r = requests.post(
        f'{PINECONE_HOST}/vectors/upsert',
        headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
        json={'vectors': [{'id': id_, 'values': vec, 'metadata': metadata}],
              'namespace': NAMESPACE},
        timeout=30
    )
    return r.ok


def search_docs(query, top_k=5, service_filter=None):
    """Search API docs."""
    vec = embed(query)
    body = {
        'vector': vec, 'topK': top_k, 'namespace': NAMESPACE,
        'includeMetadata': True
    }
    if service_filter:
        body['filter'] = {'service': {'$eq': service_filter}}
    
    r = requests.post(
        f'{PINECONE_HOST}/query',
        headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
        json=body, timeout=30
    )
    return r.json().get('matches', []) if r.ok else []


# ─── Commands ───

def cmd_log(args):
    """Log a working API pattern."""
    id_ = make_id(args.service, args.title)
    search_text = f"[{args.service}] {args.title}. {args.content}"
    tags = [t.strip() for t in args.tags.split(',')] if args.tags else []
    
    meta = {
        'service': args.service,
        'title': args.title,
        'content': args.content[:1000],
        'type': args.type if hasattr(args, 'type') else 'pattern',
        'tags': ','.join(tags),
        'updated': datetime.now().strftime('%Y-%m-%d'),
    }
    
    if upsert(id_, search_text, meta):
        icon = {'pattern': '✅', 'gotcha': '⚠️', 'snippet': '💻', 'auth': '🔑', 'ratelimit': '📊'}.get(meta['type'], '📝')
        print(f"{icon} Logged: [{args.service}] {args.title}")
        print(f"   ID: {id_}")
    else:
        print(f"❌ Failed to log")


def cmd_gotcha(args):
    args.type = 'gotcha'
    cmd_log(args)


def cmd_snippet(args):
    args.type = 'snippet'
    cmd_log(args)


def cmd_search(args):
    """Search API docs."""
    matches = search_docs(args.query, top_k=args.limit or 5,
                          service_filter=args.service if hasattr(args, 'service') and args.service else None)
    
    if matches:
        print(f"🔍 {len(matches)} results for '{args.query}':\n")
        for m in matches:
            meta = m.get('metadata', {})
            score = m.get('score', 0)
            icon = {'pattern': '✅', 'gotcha': '⚠️', 'snippet': '💻', 'auth': '🔑', 'ratelimit': '📊'}.get(meta.get('type', ''), '📝')
            print(f"  {icon} [{meta.get('service', '?')}] {meta.get('title', '?')} (score: {score:.3f})")
            if meta.get('content'):
                print(f"    {meta['content'][:200]}")
            if meta.get('tags'):
                print(f"    Tags: {meta['tags']}")
            print()
    else:
        print(f"No results for '{args.query}'")


def cmd_list(args):
    """List all docs for a service (uses broad query)."""
    matches = search_docs(f"{args.service} API documentation patterns gotchas",
                          top_k=20, service_filter=args.service)
    
    if matches:
        print(f"📚 [{args.service}] — {len(matches)} entries:\n")
        for m in matches:
            meta = m.get('metadata', {})
            icon = {'pattern': '✅', 'gotcha': '⚠️', 'snippet': '💻', 'auth': '🔑', 'ratelimit': '📊'}.get(meta.get('type', ''), '📝')
            print(f"  {icon} {meta.get('title', '?')}")
            if meta.get('content'):
                print(f"    {meta['content'][:120]}")
            print()
    else:
        print(f"No entries for {args.service}")


def cmd_batch(args):
    """Batch import from JSON file."""
    with open(args.file) as f:
        entries = json.load(f)
    
    success = 0
    for e in entries:
        id_ = make_id(e['service'], e['title'])
        search_text = f"[{e['service']}] {e['title']}. {e['content']}"
        meta = {
            'service': e['service'], 'title': e['title'],
            'content': e['content'][:1000], 'type': e.get('type', 'pattern'),
            'tags': e.get('tags', ''), 'updated': datetime.now().strftime('%Y-%m-%d'),
        }
        if upsert(id_, search_text, meta):
            success += 1
            print(f"  ✅ [{e['service']}] {e['title']}")
        else:
            print(f"  ❌ [{e['service']}] {e['title']}")
    
    print(f"\n📚 Imported {success}/{len(entries)} entries")


def main():
    parser = argparse.ArgumentParser(description="Sai's API troubleshooting knowledge base")
    sub = parser.add_subparsers(dest='command')
    
    # log
    p = sub.add_parser('log', help='Log a working API pattern')
    p.add_argument('--service', '-s', required=True)
    p.add_argument('--title', '-t', required=True)
    p.add_argument('--content', '-c', required=True)
    p.add_argument('--tags', help='Comma-separated tags')
    p.add_argument('--type', default='pattern', choices=['pattern', 'gotcha', 'snippet', 'auth', 'ratelimit'])
    
    # gotcha
    p = sub.add_parser('gotcha', help='Log a gotcha / broken thing')
    p.add_argument('--service', '-s', required=True)
    p.add_argument('--title', '-t', required=True)
    p.add_argument('--content', '-c', required=True)
    p.add_argument('--tags', help='Comma-separated tags')
    
    # snippet
    p = sub.add_parser('snippet', help='Log a working code snippet')
    p.add_argument('--service', '-s', required=True)
    p.add_argument('--title', '-t', required=True)
    p.add_argument('--content', '-c', required=True)
    p.add_argument('--tags', help='Comma-separated tags')
    
    # search
    p = sub.add_parser('search', help='Search API docs')
    p.add_argument('query')
    p.add_argument('--service', '-s', help='Filter by service')
    p.add_argument('--limit', '-l', type=int, default=5)
    
    # list
    p = sub.add_parser('list', help='List entries for a service')
    p.add_argument('--service', '-s', required=True)
    
    # batch
    p = sub.add_parser('batch', help='Batch import from JSON')
    p.add_argument('file', help='Path to JSON file')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    
    cmds = {
        'log': cmd_log, 'gotcha': cmd_gotcha, 'snippet': cmd_snippet,
        'search': cmd_search, 'list': cmd_list, 'batch': cmd_batch,
    }
    cmds[args.command](args)


if __name__ == '__main__':
    main()
