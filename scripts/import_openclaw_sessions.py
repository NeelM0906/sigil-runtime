#!/usr/bin/env python3
"""Import OpenClaw JSONL sessions into Sigil's SQLite conversation_turns.

Usage:
    PYTHONPATH=src python scripts/import_openclaw_sessions.py [--agent main] [--tenant tenant-openclaw-main]

Source: ~/.openclaw/agents/<agent>/sessions/*.jsonl
Target: .runtime/tenants/<tenant>/bomba_runtime.db → conversation_turns table
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Agent → tenant mapping
AGENT_TENANT_MAP = {
    "main": "tenant-openclaw-main",
    "forge": "tenant-openclaw-forge",
    "scholar": "tenant-openclaw-scholar",
    "recovery": "tenant-openclaw-recovery",
    "memory": "tenant-openclaw-memory",
}

# Agent → being_id mapping (for user_id field)
AGENT_BEING_MAP = {
    "main": "prime",
    "forge": "forge",
    "scholar": "scholar",
    "recovery": "recovery",
    "memory": "sai-memory",
}


def extract_text_content(content) -> str:
    """Extract text from OpenClaw message content (string or array of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool_use: {block.get('name', 'unknown')}]")
                elif block.get("type") == "tool_result":
                    parts.append(f"[tool_result: {str(block.get('content', ''))[:200]}]")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def parse_jsonl_session(path: Path) -> list[dict]:
    """Parse an OpenClaw JSONL session file into user/assistant turn pairs."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Extract session metadata
    session_meta = None
    messages = []
    for entry in lines:
        if entry.get("type") == "session":
            session_meta = entry
        elif entry.get("type") == "message":
            msg = entry.get("message", {})
            if msg.get("role") in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": extract_text_content(msg.get("content", "")),
                    "timestamp": entry.get("timestamp", ""),
                    "id": entry.get("id", ""),
                })

    session_id = session_meta.get("id", path.stem) if session_meta else path.stem
    timestamp = session_meta.get("timestamp", "") if session_meta else ""

    # Pair user/assistant messages into turns
    turns = []
    turn_number = 0
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg["role"] == "user":
            user_text = msg["content"]
            assistant_text = ""
            ts = msg["timestamp"]
            # Look ahead for assistant response
            if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                assistant_text = messages[i + 1]["content"]
                i += 1
            turn_number += 1
            turns.append({
                "session_id": session_id,
                "turn_number": turn_number,
                "user_message": user_text,
                "assistant_message": assistant_text,
                "timestamp": ts or timestamp,
            })
        elif msg["role"] == "assistant" and not turns:
            # Orphan assistant message at start — skip
            pass
        i += 1

    return turns


def import_sessions(
    agent: str,
    tenant_id: str,
    runtime_home: str = ".runtime",
    openclaw_home: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Import all JSONL sessions for an agent into Sigil's SQLite."""
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.memory.hybrid import HybridMemoryStore

    if openclaw_home is None:
        openclaw_home = str(Path.home() / ".openclaw")

    sessions_dir = Path(openclaw_home) / "agents" / agent / "sessions"
    if not sessions_dir.exists():
        log.warning("No sessions directory: %s", sessions_dir)
        return {"imported": 0, "skipped": 0, "errors": 0}

    # Initialize the tenant DB (creates tables if needed)
    tenant_dir = Path(runtime_home) / "tenants" / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    db_path = tenant_dir / "bomba_runtime.db"
    db = RuntimeDB(str(db_path))
    memory_root = tenant_dir / "memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    store = HybridMemoryStore(db=db, memory_root=memory_root)

    being_id = AGENT_BEING_MAP.get(agent, agent)
    jsonl_files = sorted(sessions_dir.glob("*.jsonl"))
    stats = {"imported": 0, "skipped": 0, "errors": 0, "turns": 0, "sessions": 0}

    for jsonl_path in jsonl_files:
        try:
            turns = parse_jsonl_session(jsonl_path)
            if not turns:
                stats["skipped"] += 1
                continue

            session_id = turns[0]["session_id"]
            log.info(
                "Importing session %s (%d turns) from %s",
                session_id[:12], len(turns), jsonl_path.name,
            )

            if dry_run:
                stats["sessions"] += 1
                stats["turns"] += len(turns)
                continue

            for turn in turns:
                turn_id = f"import-{uuid.uuid4().hex[:8]}"
                token_est = max(1, (len(turn["user_message"]) + len(turn["assistant_message"])) // 4)
                try:
                    store.record_turn(
                        tenant_id=tenant_id,
                        session_id=f"openclaw-{session_id}",
                        turn_id=turn_id,
                        user_id=being_id,
                        user_message=turn["user_message"],
                        assistant_message=turn["assistant_message"],
                    )
                    stats["turns"] += 1
                except Exception as exc:
                    log.debug("Turn insert error (may be duplicate): %s", exc)

            stats["sessions"] += 1
            stats["imported"] += 1

        except Exception as exc:
            log.error("Failed to parse %s: %s", jsonl_path.name, exc)
            stats["errors"] += 1

    db.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import OpenClaw sessions into Sigil")
    parser.add_argument("--agent", default="main", help="OpenClaw agent name (default: main)")
    parser.add_argument("--tenant", default=None, help="Target tenant ID (auto-mapped from agent if omitted)")
    parser.add_argument("--runtime-home", default=".runtime", help="Sigil runtime home dir")
    parser.add_argument("--openclaw-home", default=None, help="OpenClaw home dir (default: ~/.openclaw)")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write to DB")
    parser.add_argument("--all", action="store_true", help="Import all agents")
    args = parser.parse_args()

    agents = list(AGENT_TENANT_MAP.keys()) if args.all else [args.agent]

    for agent in agents:
        tenant = args.tenant or AGENT_TENANT_MAP.get(agent, f"tenant-{agent}")
        log.info("=== Importing agent=%s → tenant=%s ===", agent, tenant)
        stats = import_sessions(
            agent=agent,
            tenant_id=tenant,
            runtime_home=args.runtime_home,
            openclaw_home=args.openclaw_home,
            dry_run=args.dry_run,
        )
        log.info(
            "Result: %d sessions imported, %d turns, %d skipped, %d errors",
            stats.get("sessions", 0), stats.get("turns", 0),
            stats.get("skipped", 0), stats.get("errors", 0),
        )


if __name__ == "__main__":
    main()
