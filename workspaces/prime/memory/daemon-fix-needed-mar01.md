# FULL_POWER_DAEMON Fix Needed — March 1, 2026

## Problem
Daemon keeps dying from SQLite "database is locked" errors. Even with WAL mode enabled and threads reduced from 110 to 22.

## Root Cause  
Multiple worker threads trying to write to SQLite simultaneously. SQLite can only handle one writer at a time even in WAL mode.

## Fix Options
1. **Add retry with backoff** on database writes (quick fix)
2. **Use a write queue** — single writer thread, workers queue their results
3. **Switch to PostgreSQL/Supabase** for the colosseum DB (bigger change)
4. **Reduce to 1 thread per domain** (11 total — might be slow but stable)

## Current State
- Colosseum frozen at 9,119 beings / Gen 726 since ~3:30 AM
- FULL_POWER_DAEMON.py backed up as .bak.threads
- THREADS_PER_DOMAIN changed from 10 to 2 (line 77)
- WAL mode enabled on all DBs
- Daemon crashes ~30 min after restart

## For Codex
File: /Users/samantha/Projects/colosseum/FULL_POWER_DAEMON.py
Fix the `DomainWorker` class to add sqlite3 write retry with exponential backoff (max 5 retries, starting at 100ms).
