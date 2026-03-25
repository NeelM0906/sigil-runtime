#!/usr/bin/env python3
"""
Smart Compaction — Dump context to Postgres at 50% threshold, then trim memory files.

For ALL sisters (prime, recovery, scholar, forge, memory).
Runs as a cron replacement for the old "memory sync every 30 min" spam.

Flow:
1. Check context usage (token count vs max)
2. If >50%: extract key learnings from recent session transcript
3. Dump to sai_memory (Postgres) with proper tagging
4. Trim the memory/*.md files that were dumped
5. If >80%: aggressive trim — archive old daily files

Usage:
    python3 smart_compaction.py --agent scholar --check-only
    python3 smart_compaction.py --agent recovery --force
    python3 smart_compaction.py --agent all
"""

import argparse
import json
import os
import re
import sys
import glob
from datetime import datetime, timedelta
from pathlib import Path

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Agent workspace paths
AGENT_WORKSPACES = {
    "main": Path.home() / ".openclaw/workspace",
    "recovery": Path.home() / ".openclaw/workspace/sisters/sai-recovery",
    "scholar": Path.home() / ".openclaw/workspace-scholar",
    "forge": Path.home() / ".openclaw/workspace-forge",
    "memory": Path.home() / ".openclaw/workspace-memory",
}

# Agent session dirs
AGENT_SESSIONS = {
    "main": Path.home() / ".openclaw/agents/main/sessions",  # or workspace root
    "recovery": Path.home() / ".openclaw/agents/recovery/sessions",
    "scholar": Path.home() / ".openclaw/agents/scholar/sessions",
    "forge": Path.home() / ".openclaw/agents/forge/sessions",
    "memory": Path.home() / ".openclaw/agents/memory/sessions",
}

SOFT_THRESHOLD = 0.50  # Start dumping at 50%
HARD_THRESHOLD = 0.80  # Aggressive trim at 80%


def get_session_stats(agent: str) -> dict:
    """Get token usage for an agent's sessions."""
    session_dir = AGENT_SESSIONS.get(agent)
    if not session_dir or not session_dir.exists():
        return {"total_tokens": 0, "sessions": 0, "largest_file_mb": 0}

    store_path = session_dir / "sessions.json"
    if not store_path.exists():
        return {"total_tokens": 0, "sessions": 0, "largest_file_mb": 0}

    with open(store_path) as f:
        store = json.load(f)

    total_tokens = 0
    count = 0
    largest_file = 0

    for key, session in store.items():
        if isinstance(session, dict) and "totalTokens" in session:
            total_tokens += session["totalTokens"]
            count += 1

    # Check actual transcript file sizes
    for jsonl in session_dir.glob("*.jsonl"):
        size_mb = jsonl.stat().st_size / (1024 * 1024)
        largest_file = max(largest_file, size_mb)

    return {
        "total_tokens": total_tokens,
        "sessions": count,
        "largest_file_mb": round(largest_file, 1),
    }


def get_memory_files(agent: str) -> list[Path]:
    """Get all memory/*.md files for an agent, sorted by date (oldest first)."""
    workspace = AGENT_WORKSPACES.get(agent)
    if not workspace:
        return []

    memory_dir = workspace / "memory"
    if not memory_dir.exists():
        return []

    files = sorted(memory_dir.glob("*.md"))
    return files


def extract_memories_from_file(filepath: Path) -> list[dict]:
    """Parse a memory file and extract structured memories."""
    text = filepath.read_text()
    if not text.strip():
        return []

    # Use LLM to extract structured memories
    if not OPENROUTER_KEY:
        # Fallback: just chunk the text
        return [{
            "content": text[:4000],
            "category": "daily_log",
            "source": f"file:{filepath.name}",
            "importance": 5,
        }]

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json={
            "model": "anthropic/claude-sonnet-4",
            "messages": [
                {
                    "role": "system",
                    "content": "Extract structured memories from this daily log. Return a JSON array of objects with: content (the memory, 1-3 sentences), category (decision|teaching|lesson|zone_action|person|technical|principle), importance (1-10), tags (array of keywords). Focus on durable knowledge — skip transient status updates. Max 20 memories.",
                },
                {"role": "user", "content": f"File: {filepath.name}\n\n{text[:8000]}"},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()["choices"][0]["message"]["content"]

    # Parse JSON from response
    try:
        # Find JSON array in response
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            memories = json.loads(match.group())
            for m in memories:
                m["source"] = f"file:{filepath.name}"
            return memories
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback
    return [{
        "content": text[:4000],
        "category": "daily_log",
        "source": f"file:{filepath.name}",
        "importance": 5,
    }]


def dump_to_postgres(memories: list[dict], agent: str) -> int:
    """Insert memories into sai_memory table."""
    if not memories:
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for m in memories:
        rows.append({
            "content": m["content"][:4000],
            "category": m.get("category", "daily_log"),
            "source": m.get("source", f"compaction:{agent}"),
            "importance": m.get("importance", 5),
            "session_date": today,
            "sister": agent if agent != "main" else "prime",
            "tags": m.get("tags"),
            "active": True,
        })

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/sai_memory",
        headers=HEADERS,
        json=rows,
        timeout=30,
    )

    if resp.status_code in (200, 201):
        return len(rows)
    else:
        print(f"  ⚠️ Postgres insert failed: {resp.status_code} {resp.text[:200]}")
        return 0


def trim_memory_files(agent: str, aggressive: bool = False):
    """Trim old memory files after dumping to Postgres."""
    files = get_memory_files(agent)
    if not files:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    trimmed = 0
    for f in files:
        # Never touch today or yesterday
        if today in f.name or yesterday in f.name:
            continue

        # Skip non-date files (like archives, questionnaires, etc.)
        if not re.match(r"\d{4}-\d{2}-\d{2}", f.name):
            continue

        if aggressive:
            # At 80%+: delete files older than 2 days (already in Postgres)
            f.unlink()
            trimmed += 1
            print(f"  🗑️  Deleted: {f.name}")
        else:
            # At 50%+: truncate to just headers/summaries (keep first 20 lines)
            lines = f.read_text().splitlines()
            if len(lines) > 20:
                f.write_text("\n".join(lines[:20]) + f"\n\n<!-- Compacted to Postgres on {today} -->\n")
                trimmed += 1
                print(f"  ✂️  Truncated: {f.name} ({len(lines)} → 20 lines)")

    if trimmed:
        print(f"  📦 Trimmed {trimmed} files")


def trim_transcripts(agent: str, aggressive: bool = False):
    """Trim bloated session transcripts."""
    session_dir = AGENT_SESSIONS.get(agent)
    if not session_dir or not session_dir.exists():
        return

    keep_lines = 200 if aggressive else 500
    trimmed = 0

    for jsonl in session_dir.glob("*.jsonl"):
        size_mb = jsonl.stat().st_size / (1024 * 1024)
        if size_mb > 2.0:  # Only trim files > 2MB
            # Count lines
            with open(jsonl) as f:
                lines = f.readlines()

            if len(lines) > keep_lines:
                # Backup first time only
                backup_dir = session_dir / "backup"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"{jsonl.stem}-compact-{datetime.now().strftime('%Y%m%d')}.jsonl"
                if not backup_path.exists():
                    jsonl.rename(backup_path)
                    with open(jsonl, "w") as f:
                        f.writelines(lines[-keep_lines:])
                else:
                    with open(jsonl, "w") as f:
                        f.writelines(lines[-keep_lines:])

                new_size = jsonl.stat().st_size / (1024 * 1024)
                print(f"  ✂️  Transcript: {jsonl.name} ({size_mb:.1f}MB → {new_size:.1f}MB)")
                trimmed += 1

    if trimmed:
        print(f"  📦 Trimmed {trimmed} transcripts")


def compact_agent(agent: str, check_only: bool = False, force: bool = False):
    """Run smart compaction for one agent."""
    print(f"\n{'='*50}")
    print(f"🧠 {agent.upper()}")
    print(f"{'='*50}")

    stats = get_session_stats(agent)
    print(f"  Sessions: {stats['sessions']}")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    print(f"  Largest transcript: {stats['largest_file_mb']}MB")

    # Determine context model limits (approximate)
    model_limits = {
        "main": 1_000_000,
        "recovery": 200_000,
        "scholar": 200_000,
        "forge": 200_000,
        "memory": 200_000,
    }
    max_tokens = model_limits.get(agent, 200_000)
    usage_pct = stats["total_tokens"] / max_tokens if max_tokens > 0 else 0

    print(f"  Context usage: {usage_pct:.0%} ({stats['total_tokens']:,} / {max_tokens:,})")

    memory_files = get_memory_files(agent)
    print(f"  Memory files: {len(memory_files)}")

    if check_only:
        if usage_pct >= HARD_THRESHOLD:
            print(f"  🔴 CRITICAL — over {HARD_THRESHOLD:.0%} threshold")
        elif usage_pct >= SOFT_THRESHOLD:
            print(f"  🟡 WARNING — over {SOFT_THRESHOLD:.0%} threshold")
        else:
            print(f"  🟢 OK")
        return

    needs_soft = usage_pct >= SOFT_THRESHOLD or force
    needs_hard = usage_pct >= HARD_THRESHOLD

    if not needs_soft and not force:
        print(f"  🟢 Under threshold — skipping")
        return

    # Step 1: Extract and dump memories to Postgres
    total_dumped = 0
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    for mf in memory_files:
        # Skip today/yesterday for soft compaction
        if not needs_hard and (today in mf.name or yesterday in mf.name):
            continue
        if not re.match(r"\d{4}-\d{2}-\d{2}", mf.name):
            continue

        print(f"  📤 Extracting: {mf.name}")
        memories = extract_memories_from_file(mf)
        if memories:
            count = dump_to_postgres(memories, agent)
            total_dumped += count
            print(f"     → {count} memories to Postgres")

    print(f"  📊 Total memories dumped: {total_dumped}")

    # Step 2: Trim memory files
    trim_memory_files(agent, aggressive=needs_hard)

    # Step 3: Trim bloated transcripts
    trim_transcripts(agent, aggressive=needs_hard)

    print(f"  ✅ Compaction complete")


def main():
    parser = argparse.ArgumentParser(description="Smart compaction for ACT-I sisters")
    parser.add_argument("--agent", default="all", help="Agent to compact (main/recovery/scholar/forge/memory/all)")
    parser.add_argument("--check-only", action="store_true", help="Just check thresholds, don't compact")
    parser.add_argument("--force", action="store_true", help="Force compaction regardless of threshold")
    args = parser.parse_args()

    agents = list(AGENT_WORKSPACES.keys()) if args.agent == "all" else [args.agent]

    print(f"🔥 Smart Compaction — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Soft threshold: {SOFT_THRESHOLD:.0%} | Hard threshold: {HARD_THRESHOLD:.0%}")

    for agent in agents:
        if agent not in AGENT_WORKSPACES:
            print(f"⚠️ Unknown agent: {agent}")
            continue
        compact_agent(agent, check_only=args.check_only, force=args.force)

    print(f"\n{'='*50}")
    print(f"🏁 Done")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
