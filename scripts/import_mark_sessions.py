#!/usr/bin/env python3
"""Import Mark's OpenClaw conversation logs into Sigil.

Writes to:
  1. conversation_turns in tenant-recovery-mark DB (Recovery's memory)
  2. mc_messages in main dashboard DB (Mark's chat UI)

Usage:
    PYTHONPATH=src python scripts/import_mark_sessions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SOURCE_DIR = Path("/Users/studio2/Downloads/mark_sai_recovery_marc24")
TENANT_ID = "tenant-recovery-mark"
USER_ID = "user-00ab3737"
BEING_ID = "recovery"
RUNTIME_HOME = Path(".runtime")


def extract_text(content) -> str:
    """Extract text from OpenClaw message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool: {block.get('name', '?')}]")
                elif block.get("type") == "tool_result":
                    c = block.get("content", "")
                    if isinstance(c, list):
                        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                    parts.append(f"[result: {str(c)[:200]}]")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return str(content)


def parse_session(path: Path) -> dict:
    """Parse a JSONL session file into metadata + message pairs."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    meta = next((e for e in entries if e.get("type") == "session"), {})
    session_id = meta.get("id", path.stem)
    session_ts = meta.get("timestamp", "")

    messages = []
    for e in entries:
        if e.get("type") != "message":
            continue
        msg = e.get("message", {})
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        text = extract_text(msg.get("content", ""))
        if not text.strip():
            continue
        messages.append({
            "role": role,
            "text": text,
            "timestamp": e.get("timestamp", session_ts),
            "id": e.get("id", uuid.uuid4().hex[:8]),
        })

    return {
        "session_id": session_id,
        "timestamp": session_ts,
        "messages": messages,
    }


def import_all(dry_run: bool = False):
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.memory.hybrid import HybridMemoryStore

    if not SOURCE_DIR.exists():
        log.error("Source directory not found: %s", SOURCE_DIR)
        return

    # Open tenant DB for conversation_turns
    tenant_dir = RUNTIME_HOME / "tenants" / TENANT_ID
    tenant_dir.mkdir(parents=True, exist_ok=True)
    tenant_db = RuntimeDB(str(tenant_dir / "bomba_runtime.db"))
    memory_root = tenant_dir / "memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    store = HybridMemoryStore(db=tenant_db, memory_root=memory_root)

    # Open main dashboard DB for mc_messages + mc_chat_sessions
    main_db = RuntimeDB(str(RUNTIME_HOME / "bomba_runtime.db"))

    jsonl_files = sorted(SOURCE_DIR.glob("*.jsonl"))
    total_turns = 0
    total_msgs = 0
    total_sessions = 0

    for path in jsonl_files:
        session = parse_session(path)
        messages = session["messages"]
        if not messages:
            log.info("  Skipping empty session: %s", path.name)
            continue

        sid = session["session_id"]
        session_ts = session["timestamp"] or datetime.now(timezone.utc).isoformat()
        chat_session_id = f"mark-recovery-{sid[:12]}"
        sigil_session_id = f"mc-chat-{chat_session_id}-recovery"

        user_count = sum(1 for m in messages if m["role"] == "user")
        asst_count = sum(1 for m in messages if m["role"] == "assistant")
        log.info("Session %s | %s | %d user + %d assistant msgs", sid[:12], session_ts[:10], user_count, asst_count)

        if dry_run:
            total_sessions += 1
            total_msgs += len(messages)
            continue

        # 1. Create chat session in dashboard
        try:
            main_db.execute_commit(
                """INSERT OR IGNORE INTO mc_chat_sessions (id, name, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (chat_session_id, f"Mark — {session_ts[:10]}", session_ts, session_ts),
            )
        except Exception as exc:
            log.debug("Session insert: %s", exc)

        # 2. Import messages
        turn_user = None
        for msg in messages:
            ts = msg["timestamp"] or session_ts
            msg_id = f"import-{msg['id']}"

            # Dashboard message
            try:
                sender = "user" if msg["role"] == "user" else BEING_ID
                main_db.execute_commit(
                    """INSERT OR IGNORE INTO mc_messages
                       (id, sender, content, type, mode, session_id, task_ref, created_at, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (msg_id, sender, msg["text"], "direct", "auto", chat_session_id, None, ts, None),
                )
                total_msgs += 1
            except Exception as exc:
                log.debug("Message insert: %s", exc)

            # Conversation turn (pair user+assistant)
            if msg["role"] == "user":
                turn_user = msg
            elif msg["role"] == "assistant" and turn_user is not None:
                try:
                    store.record_turn(
                        tenant_id=TENANT_ID,
                        session_id=sigil_session_id,
                        turn_id=f"import-{uuid.uuid4().hex[:8]}",
                        user_id=USER_ID,
                        user_message=turn_user["text"],
                        assistant_message=msg["text"],
                    )
                    total_turns += 1
                except Exception as exc:
                    log.debug("Turn insert: %s", exc)
                turn_user = None

        total_sessions += 1

    tenant_db.close()
    main_db.close()

    log.info("=== Import complete ===")
    log.info("Sessions: %d", total_sessions)
    log.info("Dashboard messages: %d", total_msgs)
    log.info("Conversation turns: %d", total_turns)


def main():
    parser = argparse.ArgumentParser(description="Import Mark's conversation logs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
