#!/usr/bin/env python3
"""
worklog.py — Sai's working memory that survives session resets.

Tracks what I'm doing, thinking, and where I left off.
Writes to Postgres (sai_session_state) + Pinecone (saimemory/worklog).

Usage:
  # Start working on something
  python3 worklog.py start --project creative-forge --task "Generate Cayman eps 6-10" \
    --details "Series bible has 10 eps mapped. 1-5 done. Using Seedance 2.0 for scenes." \
    --next "Run generate-ep06-07.py, then assemble with ffmpeg"

  # Update progress on current task
  python3 worklog.py update --id <uuid> --details "Ep 6-7 scenes generating on fal.ai" --status in_progress

  # Log a thought/decision (no task, just context)
  python3 worklog.py note --project creative-forge \
    --details "Seedance 2.0 handles cartoon animals better than Kling v3. Stick with it for series."

  # Mark something done
  python3 worklog.py done --id <uuid> --deliverable "Episodes 6-10 generated and delivered"

  # Block something
  python3 worklog.py block --id <uuid> --blocker "Need Aiko to review ep 5 before continuing"

  # See what I'm working on RIGHT NOW
  python3 worklog.py status
  python3 worklog.py status --project creative-forge

  # Wake up from reset — what was I doing?
  python3 worklog.py resume

  # Search past work
  python3 worklog.py search "cayman video generation"
"""

import os
import sys
import json
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

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_HOST = 'https://saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io'
EMBED_MODEL = 'openai/text-embedding-3-small'

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}
TABLE = 'sai_session_state'


def embed(text):
    """Get embedding via OpenRouter."""
    r = requests.post(
        'https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
        json={'model': EMBED_MODEL, 'input': [text]},
        timeout=30
    )
    r.raise_for_status()
    return r.json()['data'][0]['embedding']


def pin_upsert(id_, text, metadata):
    """Upsert to Pinecone saimemory/worklog namespace."""
    try:
        vec = embed(text)
        r = requests.post(
            f'{PINECONE_HOST}/vectors/upsert',
            headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
            json={'vectors': [{'id': f'worklog-{id_}', 'values': vec, 'metadata': metadata}],
                  'namespace': 'worklog'},
            timeout=30
        )
        return r.ok
    except Exception as e:
        print(f'⚠️ Pinecone: {e}')
        return False


def pg_insert(data):
    """Insert row into sai_session_state."""
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/{TABLE}',
        headers={**HEADERS, 'Prefer': 'return=representation'},
        json=data
    )
    if not r.ok:
        print(f'❌ Postgres error: {r.status_code} {r.text[:200]}')
        return None
    return r.json()[0] if r.json() else None


def pg_update(id_, data):
    """Update row by ID."""
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    r = requests.patch(
        f'{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{id_}',
        headers={**HEADERS, 'Prefer': 'return=representation'},
        json=data
    )
    if not r.ok:
        print(f'❌ Postgres error: {r.status_code} {r.text[:200]}')
        return None
    return r.json()[0] if r.json() else None


def pg_query(filters=None, order='created_at.desc', limit=10):
    """Query rows with optional filters."""
    url = f'{SUPABASE_URL}/rest/v1/{TABLE}?order={order}&limit={limit}'
    if filters:
        url += '&' + '&'.join(f'{k}=eq.{v}' for k, v in filters.items())
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []


def format_row(row, verbose=False):
    """Pretty print a worklog entry."""
    status_icons = {
        'in_progress': '🔨', 'paused': '⏸️', 'completed': '✅',
        'blocked': '🚫', 'note': '📝', 'idea': '💡', 'active': '🔨'
    }
    icon = status_icons.get(row.get('status', ''), '❓')
    project = row.get('priority', 'unknown')  # We repurpose priority as project
    task = row.get('task', 'untitled')
    ts = row.get('created_at', '')[:16].replace('T', ' ')
    
    out = f"{icon} [{project}] {task}"
    if verbose:
        out += f"\n   ID: {row['id']}"
        out += f"\n   Created: {ts}"
        if row.get('context'):
            out += f"\n   Context: {row['context'][:200]}"
        if row.get('blocker') and row['blocker'] != 'None':
            out += f"\n   Blocker: {row['blocker']}"
        if row.get('deliverable') and row['deliverable'] != 'None':
            out += f"\n   Deliverable: {row['deliverable']}"
    return out


# ─── Commands ───

def cmd_start(args):
    """Start a new task."""
    now = datetime.now(timezone.utc).isoformat()
    data = {
        'task': args.task,
        'status': 'in_progress',
        'priority': args.project,  # Repurpose priority field for project name
        'owner': 'sai',
        'context': args.details or '',
        'blocker': args.next or '',  # Repurpose blocker for next_steps when status != blocked
        'started_at': now,
    }
    row = pg_insert(data)
    if row:
        # Also embed in Pinecone
        search_text = f"[{args.project}] {args.task}. {args.details or ''} Next: {args.next or ''}"
        pin_upsert(row['id'], search_text, {
            'project': args.project, 'task': args.task, 'status': 'in_progress',
            'details': (args.details or '')[:500], 'created': now[:10]
        })
        print(f"✅ Started: {args.task}")
        print(f"   ID: {row['id']}")
        print(f"   Project: {args.project}")
    return row


def cmd_update(args):
    """Update an existing task."""
    data = {}
    if args.details:
        data['context'] = args.details
    if args.status:
        data['status'] = args.status
    if args.next:
        data['blocker'] = args.next  # next_steps in blocker field when not blocked
    
    row = pg_update(args.id, data)
    if row:
        search_text = f"[{row.get('priority', '?')}] {row['task']}. {row.get('context', '')}"
        pin_upsert(row['id'], search_text, {
            'project': row.get('priority', ''), 'task': row['task'],
            'status': row.get('status', ''), 'details': (row.get('context') or '')[:500],
            'updated': datetime.now().strftime('%Y-%m-%d')
        })
        print(f"✅ Updated: {row['task']}")


def cmd_note(args):
    """Log a thought or decision — not a task, just context."""
    now = datetime.now(timezone.utc).isoformat()
    data = {
        'task': args.title or f"Note — {datetime.now().strftime('%b %d %I:%M %p')}",
        'status': 'note',
        'priority': args.project,
        'owner': 'sai',
        'context': args.details,
        'started_at': now,
        'completed_at': now,
    }
    row = pg_insert(data)
    if row:
        pin_upsert(row['id'], f"[{args.project}] {data['task']}. {args.details}", {
            'project': args.project, 'task': data['task'], 'status': 'note',
            'details': (args.details or '')[:500], 'created': now[:10]
        })
        print(f"📝 Noted: {data['task']}")


def cmd_done(args):
    """Mark task completed."""
    data = {
        'status': 'completed',
        'completed_at': datetime.now(timezone.utc).isoformat(),
    }
    if args.deliverable:
        data['deliverable'] = args.deliverable
    row = pg_update(args.id, data)
    if row:
        print(f"✅ Completed: {row['task']}")


def cmd_block(args):
    """Mark task as blocked."""
    data = {'status': 'blocked', 'blocker': args.blocker}
    row = pg_update(args.id, data)
    if row:
        print(f"🚫 Blocked: {row['task']} — {args.blocker}")


def cmd_status(args):
    """Show active work."""
    filters = {}
    if args.project:
        filters['priority'] = args.project
    
    # Get in-progress and blocked items
    active = pg_query({'status': 'in_progress', **(filters)}, limit=20)
    blocked = pg_query({'status': 'blocked', **(filters)}, limit=10)
    paused = pg_query({'status': 'paused', **(filters)}, limit=10)
    
    print("═══ SAI WORKLOG ═══")
    
    if active:
        print(f"\n🔨 In Progress ({len(active)}):")
        for r in active:
            print(f"  {format_row(r, verbose=True)}")
    
    if blocked:
        print(f"\n🚫 Blocked ({len(blocked)}):")
        for r in blocked:
            print(f"  {format_row(r, verbose=True)}")
    
    if paused:
        print(f"\n⏸️ Paused ({len(paused)}):")
        for r in paused:
            print(f"  {format_row(r, verbose=True)}")
    
    if not active and not blocked and not paused:
        print("\n✨ Nothing active. Clean slate!")
    
    # Recent completions
    recent = pg_query({'status': 'completed', **(filters)}, limit=5)
    if recent:
        print(f"\n✅ Recently Completed:")
        for r in recent:
            print(f"  {format_row(r)}")


def cmd_resume(args):
    """Wake-up command: what was I doing before reset?"""
    print("═══ RESUME — Where did I leave off? ═══\n")
    
    active = pg_query({'status': 'in_progress'}, limit=15)
    blocked = pg_query({'status': 'blocked'}, limit=10)
    
    # Recent notes (last 24h-ish)
    notes = pg_query({'status': 'note'}, limit=5)
    
    if active:
        print(f"🔨 Active Tasks ({len(active)}):")
        for r in active:
            print(f"\n  {format_row(r, verbose=True)}")
            if r.get('blocker') and r['blocker'] != 'None':
                print(f"   ➡️  Next: {r['blocker']}")
    
    if blocked:
        print(f"\n🚫 Blocked:")
        for r in blocked:
            print(f"  {format_row(r, verbose=True)}")
    
    if notes:
        print(f"\n📝 Recent Notes:")
        for r in notes:
            print(f"  {format_row(r, verbose=True)}")
    
    if not active and not blocked:
        print("✨ No active tasks. Fresh start!")


def cmd_search(args):
    """Search past work via Pinecone."""
    try:
        vec = embed(args.query)
        r = requests.post(
            f'{PINECONE_HOST}/query',
            headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
            json={'vector': vec, 'topK': args.limit or 5, 'namespace': 'worklog', 'includeMetadata': True},
            timeout=30
        )
        if r.ok:
            matches = r.json().get('matches', [])
            if matches:
                print(f"🔍 Found {len(matches)} results for '{args.query}':\n")
                for m in matches:
                    meta = m.get('metadata', {})
                    score = m.get('score', 0)
                    print(f"  [{meta.get('project', '?')}] {meta.get('task', '?')} (score: {score:.3f})")
                    if meta.get('details'):
                        print(f"    {meta['details'][:150]}")
                    print()
            else:
                print(f"No results for '{args.query}'")
        else:
            print(f"Search error: {r.status_code}")
    except Exception as e:
        print(f"Search error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sai's worklog — survives session resets")
    sub = parser.add_subparsers(dest='command')
    
    # start
    p = sub.add_parser('start', help='Start a new task')
    p.add_argument('--project', '-p', required=True, help='Project name')
    p.add_argument('--task', '-t', required=True, help='What are you doing')
    p.add_argument('--details', '-d', help='Longer context, thoughts')
    p.add_argument('--next', '-n', help='Next steps when you pick this up')
    
    # update
    p = sub.add_parser('update', help='Update existing task')
    p.add_argument('--id', required=True, help='Task UUID')
    p.add_argument('--details', '-d', help='New context')
    p.add_argument('--status', '-s', choices=['in_progress', 'paused', 'blocked', 'completed'])
    p.add_argument('--next', '-n', help='Updated next steps')
    
    # note
    p = sub.add_parser('note', help='Log a thought or decision')
    p.add_argument('--project', '-p', required=True, help='Project name')
    p.add_argument('--details', '-d', required=True, help='The note')
    p.add_argument('--title', '-t', help='Short title')
    
    # done
    p = sub.add_parser('done', help='Mark task completed')
    p.add_argument('--id', required=True, help='Task UUID')
    p.add_argument('--deliverable', '-d', help='What was delivered')
    
    # block
    p = sub.add_parser('block', help='Mark task blocked')
    p.add_argument('--id', required=True, help='Task UUID')
    p.add_argument('--blocker', '-b', required=True, help='What is blocking')
    
    # status
    p = sub.add_parser('status', help='Show active work')
    p.add_argument('--project', '-p', help='Filter by project')
    
    # resume
    sub.add_parser('resume', help='Wake-up: what was I doing?')
    
    # search
    p = sub.add_parser('search', help='Search past work')
    p.add_argument('query', help='Search query')
    p.add_argument('--limit', '-l', type=int, default=5)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cmds = {
        'start': cmd_start, 'update': cmd_update, 'note': cmd_note,
        'done': cmd_done, 'block': cmd_block, 'status': cmd_status,
        'resume': cmd_resume, 'search': cmd_search,
    }
    cmds[args.command](args)


if __name__ == '__main__':
    main()
