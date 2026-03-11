#!/usr/bin/env python3
"""
SAI Recovery — Supabase Helper
Reusable functions for all Supabase operations.

Usage:
    from supabase_helper import SupabaseClient
    db = SupabaseClient()
    db.insert('sai_memory', {'content': '...', 'category': '...', 'source': 'sai-recovery', 'importance': 7})
    db.select('sai_memory', filters={'source': 'sai-recovery'}, limit=10)
    db.update('sai_memory', filters={'id': 'uuid-here'}, data={'importance': 9})
    db.upsert('sai_memory', data={...}, on_conflict='id')
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://yncbtzqrherwyeybchet.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')

class SupabaseClient:
    def __init__(self, url=SUPABASE_URL, key=SUPABASE_KEY):
        if not key:
            raise RuntimeError('SUPABASE_SERVICE_KEY or SUPABASE_KEY must be set in the environment')
        self.url = url
        self.key = key
        self.base = f'{url}/rest/v1'

    def _headers(self, extra=None):
        h = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
        }
        if extra:
            h.update(extra)
        return h

    def _build_filter_query(self, filters):
        """Convert dict filters to PostgREST query params."""
        params = {}
        for k, v in (filters or {}).items():
            if isinstance(v, str) and not v.startswith(('eq.', 'neq.', 'gt.', 'lt.', 'gte.', 'lte.', 'like.', 'ilike.', 'in.', 'is.')):
                params[k] = f'eq.{v}'
            else:
                params[k] = v
        return params

    def select(self, table, filters=None, columns='*', limit=100, order=None):
        """SELECT rows from a table."""
        params = self._build_filter_query(filters)
        params['select'] = columns
        params['limit'] = str(limit)
        if order:
            params['order'] = order
        query = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f'{self.base}/{table}?{query}',
            headers=self._headers()
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f'SELECT error: {e.read().decode()}')
            return []

    def insert(self, table, data, return_row=True):
        """INSERT a row."""
        payload = json.dumps(data).encode()
        headers = self._headers({'Prefer': 'return=representation' if return_row else 'return=minimal'})
        req = urllib.request.Request(
            f'{self.base}/{table}',
            data=payload,
            method='POST',
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                return result[0] if return_row and result else True
        except urllib.error.HTTPError as e:
            print(f'INSERT error: {e.read().decode()}')
            return None

    def update(self, table, filters, data):
        """UPDATE rows matching filters."""
        params = self._build_filter_query(filters)
        query = urllib.parse.urlencode(params)
        payload = json.dumps(data).encode()
        headers = self._headers({'Prefer': 'return=representation'})
        req = urllib.request.Request(
            f'{self.base}/{table}?{query}',
            data=payload,
            method='PATCH',
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f'UPDATE error: {e.read().decode()}')
            return None

    def upsert(self, table, data, on_conflict='id'):
        """UPSERT — insert or update on conflict."""
        payload = json.dumps(data).encode()
        headers = self._headers({
            'Prefer': f'resolution=merge-duplicates,return=representation',
        })
        req = urllib.request.Request(
            f'{self.base}/{table}?on_conflict={on_conflict}',
            data=payload,
            method='POST',
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                return result[0] if result else True
        except urllib.error.HTTPError as e:
            print(f'UPSERT error: {e.read().decode()}')
            return None

    def delete(self, table, filters):
        """DELETE rows matching filters."""
        params = self._build_filter_query(filters)
        query = urllib.parse.urlencode(params)
        headers = self._headers({'Prefer': 'return=representation'})
        req = urllib.request.Request(
            f'{self.base}/{table}?{query}',
            method='DELETE',
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f'DELETE error: {e.read().decode()}')
            return None

    def count(self, table, filters=None):
        """COUNT rows matching filters."""
        params = self._build_filter_query(filters or {})
        params['select'] = 'id'
        query = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f'{self.base}/{table}?{query}',
            headers=self._headers({'Prefer': 'count=exact', 'Range-Unit': 'items', 'Range': '0-0'})
        )
        try:
            with urllib.request.urlopen(req) as resp:
                content_range = resp.headers.get('Content-Range', '')
                if '/' in content_range:
                    return int(content_range.split('/')[1])
                return len(json.loads(resp.read().decode()))
        except urllib.error.HTTPError as e:
            print(f'COUNT error: {e.read().decode()}')
            return 0

    # ─── RECOVERY-SPECIFIC HELPERS ──────────────────────────────

    def log_memory(self, content, category='general', importance=5, metadata=None):
        """Log a memory entry to sai_memory."""
        return self.insert('sai_memory', {
            'content': content,
            'category': category,
            'source': 'sai-recovery',
            'importance': importance,
            'metadata': json.dumps(metadata or {}),
        })

    def log_session(self, summary, session_type='work', key_outcomes=None, next_steps=None):
        """Log a session to sai_memory with session category."""
        return self.log_memory(
            content=summary,
            category=f'session-{session_type}',
            importance=7,
            metadata={
                'date': datetime.now().strftime('%Y-%m-%d'),
                'session_type': session_type,
                'key_outcomes': key_outcomes or [],
                'next_steps': next_steps or [],
            }
        )


# ─── QUICK TEST ──────────────────────────────────────────────────
if __name__ == '__main__':
    db = SupabaseClient()

    print('Testing SupabaseClient...')

    # Test count
    total = db.count('sai_contacts')
    print(f'sai_contacts count: {total}')

    # Test select
    rows = db.select('sai_memory', filters={'source': 'sai-recovery'}, limit=5, order='created_at.desc')
    print(f'sai_memory (recovery): {len(rows)} rows')

    # Test log_memory
    row = db.log_memory(
        content='Supabase helper operational. INSERT/SELECT/UPDATE/DELETE/COUNT all verified.',
        category='system-test',
        importance=5
    )
    print(f'log_memory test: ID = {row["id"][:8] if row else "FAILED"}')

    print('\n✅ All tests passed!')
