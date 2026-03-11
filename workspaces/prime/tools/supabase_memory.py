#!/usr/bin/env python3
"""
SAI Shared Memory — Supabase Postgres Client
Used by ALL sisters for compaction-proof persistent state.

Tables:
  sai_memory         — What we KNOW (permanent knowledge, decisions, lessons)
  sai_session_state  — What we're DOING (active tasks, blockers, deliverables)
  sai_conversations  — What was SAID (key moments from humans and sisters)
  sai_contacts       — CRM (169+ records)

Usage:
  from supabase_memory import mem

  # Save a memory
  mem.remember("lesson", "Kai's 17 beings validated by HOI scatter test", source="kai", importance="high")

  # Save what you're working on
  mem.working_on("Building Colosseum scoring rubrics", priority="zone_action", deliverable="80 rubric JSONs")

  # Save a key conversation moment
  mem.said("adam", "Let's go. I'm good.", significance="Green light on being architecture deployment")

  # Check what's active
  tasks = mem.active_tasks()

  # Wake up after compaction — get everything you need
  state = mem.wake_up()

  # Query memories
  memories = mem.recall(category="directive", source="sean", limit=10)
"""

import os
import json
from pathlib import Path
from datetime import datetime, date

# Load env
_env_path = Path.home() / '.openclaw' / '.env'
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client

_url = "https://yncbtzqrherwyeybchet.supabase.co"
_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
_client = create_client(_url, _key) if _key else None


class SaiMemory:
    def __init__(self, sister='prime'):
        self.sister = sister
        self.db = _client

    # ─── REMEMBER (sai_memory) ───────────────────────────────

    def remember(self, category, content, title=None, source=None, importance=5, tags=None):
        """Store a permanent memory. Categories: decision, lesson, directive, blocker, discovery, person, project
        Importance: 1-10 scale (10=critical, 7=high, 5=normal, 3=low)"""
        return self.db.table('sai_memory').insert({
            'category': category,
            'title': title or content[:100],
            'content': content,
            'source': source,
            'importance': importance if isinstance(importance, int) else {'critical': 10, 'high': 8, 'normal': 5, 'low': 3}.get(importance, 5),
            'tags': tags or [],
            'sister': self.sister,
            'active': True,
        }).execute()

    def recall(self, category=None, source=None, importance=None, limit=20, search=None):
        """Query memories with optional filters."""
        q = self.db.table('sai_memory').select('*').eq('active', True).order('created_at', desc=True).limit(limit)
        if category: q = q.eq('category', category)
        if source: q = q.eq('source', source)
        if importance: q = q.gte('importance', {'critical': 9, 'high': 7, 'normal': 4, 'low': 1}.get(importance, importance) if isinstance(importance, str) else importance)
        if search: q = q.ilike('content', f'%{search}%')
        return q.execute().data

    def forget(self, memory_id):
        """Soft-delete a memory (set active=false)."""
        return self.db.table('sai_memory').update({'active': False}).eq('id', memory_id).execute()

    # ─── WORKING ON (sai_session_state) ──────────────────────

    def working_on(self, task, priority='normal', context=None, deliverable=None, blocker=None):
        """Record what you're currently working on."""
        return self.db.table('sai_session_state').insert({
            'task': task,
            'status': 'active',
            'priority': priority,
            'owner': self.sister,
            'context': context,
            'deliverable': deliverable,
            'blocker': blocker,
        }).execute()

    def complete_task(self, task_id):
        """Mark a task as completed."""
        return self.db.table('sai_session_state').update({
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
        }).eq('id', task_id).execute()

    def block_task(self, task_id, blocker):
        """Mark a task as blocked."""
        return self.db.table('sai_session_state').update({
            'status': 'blocked',
            'blocker': blocker,
        }).eq('id', task_id).execute()

    def active_tasks(self, owner=None):
        """Get all active tasks, optionally filtered by owner."""
        q = self.db.table('sai_session_state').select('*').eq('status', 'active').order('created_at', desc=True)
        if owner: q = q.eq('owner', owner)
        return q.execute().data

    def all_tasks(self, limit=20):
        """Get recent tasks across all sisters."""
        return self.db.table('sai_session_state').select('*').order('created_at', desc=True).limit(limit).execute().data

    # ─── SAID (sai_conversations) ────────────────────────────

    def said(self, speaker, content, channel=None, significance=None, tags=None):
        """Record a key conversation moment."""
        return self.db.table('sai_conversations').insert({
            'speaker': speaker,
            'channel': channel or 'telegram',
            'content': content,
            'significance': significance,
            'tags': tags or [],
        }).execute()

    def conversations(self, speaker=None, limit=20, search=None):
        """Query recent conversations."""
        q = self.db.table('sai_conversations').select('*').order('created_at', desc=True).limit(limit)
        if speaker: q = q.eq('speaker', speaker)
        if search: q = q.ilike('content', f'%{search}%')
        return q.execute().data

    # ─── WAKE UP (compaction recovery) ───────────────────────

    def wake_up(self):
        """Called on session start after compaction. Returns everything needed to resume."""
        active = self.active_tasks()
        critical = self.recall(importance='critical', limit=10)
        recent_convos = self.conversations(limit=10)
        directives = self.recall(category='directive', limit=10)
        blockers = self.db.table('sai_session_state').select('*').eq('status', 'blocked').execute().data

        return {
            'active_tasks': active,
            'critical_memories': critical,
            'recent_conversations': recent_convos,
            'directives': directives,
            'blockers': blockers,
            'sister': self.sister,
            'woke_up_at': datetime.utcnow().isoformat(),
        }

    # ─── PRE-COMPACTION DUMP ─────────────────────────────────

    def pre_compaction_dump(self, summary, active_work=None, key_decisions=None):
        """Call this before compaction hits (~70% context). Saves everything important."""
        # Save the session summary
        self.remember(
            category='session_summary',
            content=summary,
            title=f'Session summary {date.today()}',
            source='self',
            importance='high',
            tags=['compaction', 'session_end']
        )

        # Update any active tasks with latest context
        if active_work:
            for task_desc in active_work:
                self.working_on(task_desc, priority='high', context='Saved pre-compaction')

        # Save key decisions
        if key_decisions:
            for decision in key_decisions:
                self.remember('decision', decision, source='self', importance='high', tags=['compaction'])

        return True


# Default instance — sisters override with their name
mem = SaiMemory('prime')
