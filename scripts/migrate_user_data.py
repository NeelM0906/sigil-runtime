#!/usr/bin/env python3
"""Onboard SAI Recovery users: create accounts, pull Supabase memories, verify Pinecone.

Usage:
    PYTHONPATH=src python scripts/migrate_user_data.py \
        --config users.json \
        --runtime-home .runtime
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[7:].strip()
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        if k:
            os.environ.setdefault(k, v)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_json(method: str, url: str, *, headers: dict | None = None, payload: dict | None = None) -> dict:
    data = None
    req_headers = {"Accept": "application/json", "User-Agent": "sigil-migrate/1.0"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=req_headers, method=method, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body) if body.strip() else {}


# ── Phase 1: Account creation ───────────────────────────────────────

def create_account(mc_db, user_cfg: dict, runtime_home: Path, dry_run: bool) -> str:
    """Create MC user account and tenant directory. Returns status string."""
    import bcrypt
    from bomba_sr.runtime.tenancy import TenantRegistry
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.memory.hybrid import HybridMemoryStore

    email = user_cfg["email"]
    tenant_id = user_cfg["tenant_id"]

    # Check if exists
    row = mc_db.execute("SELECT id FROM mc_users WHERE email = ?", (email,)).fetchone()
    if row:
        return "already exists"

    if dry_run:
        return "would create"

    # Insert user
    uid = f"user-{email.split('@')[0].replace('.', '-')[:16]}"
    pw_hash = bcrypt.hashpw(user_cfg["password"].encode(), bcrypt.gensalt(rounds=12)).decode()
    now = _utc_now()
    mc_db.execute_commit(
        "INSERT INTO mc_users (id, email, name, password_hash, role, tenant_id, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (uid, email, user_cfg["name"], pw_hash, user_cfg.get("role", "operator"), tenant_id, now, now),
    )

    # Create tenant directory structure
    registry = TenantRegistry(runtime_home)
    ctx = registry.ensure_tenant(tenant_id)

    # Initialize memory tables in per-tenant SQLite
    tenant_db = RuntimeDB(ctx.db_path)
    HybridMemoryStore(tenant_db, ctx.memory_root)
    tenant_db.close()

    return f"created ({tenant_id})"


# ── Phase 2: Supabase pull ──────────────────────────────────────────

def pull_supabase(user_cfg: dict, runtime_home: Path, dry_run: bool) -> int:
    """Pull structured memories from Supabase into tenant's local memory. Returns record count."""
    from bomba_sr.storage.db import RuntimeDB
    from bomba_sr.memory.consolidation import MemoryCandidate, MemoryConsolidator
    from bomba_sr.runtime.tenancy import TenantRegistry

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        print("    WARN: SUPABASE_URL or SUPABASE_SERVICE_KEY not set, skipping")
        return 0

    sister = user_cfg.get("supabase_sister")
    table = user_cfg.get("supabase_table", "sai_memory")
    being_id = user_cfg.get("being_id", "recovery")
    tenant_id = user_cfg["tenant_id"]

    if not sister:
        return 0

    # Fetch records from Supabase
    url = f"{supabase_url}/rest/v1/{table}?sister=eq.{sister}&select=*"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }

    try:
        records = _http_json("GET", url, headers=headers)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"    ERROR: Supabase fetch failed: {e}")
        return 0

    if not isinstance(records, list):
        print(f"    WARN: Unexpected Supabase response: {type(records)}")
        return 0

    if dry_run:
        print(f"    Would import {len(records)} records")
        return len(records)

    # Open tenant DB and consolidator
    registry = TenantRegistry(runtime_home)
    ctx = registry.ensure_tenant(tenant_id)
    tenant_db = RuntimeDB(ctx.db_path)
    consolidator = MemoryConsolidator(tenant_db)

    imported = 0
    for rec in records:
        # Extract ID — try multiple field names
        record_id = str(rec.get("id") or rec.get("uuid") or rec.get("memory_id") or "")
        if not record_id:
            continue

        # Extract topic/key
        topic = str(rec.get("topic") or rec.get("title") or rec.get("memory_key") or record_id)

        # Extract content — try multiple field names
        content = ""
        for field in ("content", "value", "data", "text", "body", "memory_text"):
            val = rec.get(field)
            if val and isinstance(val, str):
                content = val
                break
        if not content:
            # Try JSON-encoding the whole record as content
            content = json.dumps(rec, default=str)

        created_at = str(rec.get("created_at") or rec.get("updated_at") or _utc_now())

        key = f"supabase::{table}::{record_id}"
        candidate = MemoryCandidate(
            user_id=f"prime->{being_id}",
            key=key,
            content=content,
            tier="semantic",
            evidence_refs=(f"supabase://{table}/{record_id}",),
            recency_ts=created_at,
            being_id=being_id,
        )
        consolidator.upsert(candidate)
        tenant_db.commit()
        imported += 1
        print(f"    {key}: {topic[:60]}")

    tenant_db.close()
    return imported


# ── Phase 3: Pinecone verification ──────────────────────────────────

def verify_pinecone(user_cfg: dict) -> dict:
    """Run a test query against the user's Pinecone index. Returns result summary."""
    from bomba_sr.tools.builtin_pinecone import (
        _choose_pinecone_api_key,
        _embed_query,
        _http_json as pc_http_json,
        _resolve_index_host,
    )

    index_name = user_cfg.get("pinecone_index")
    namespace = user_cfg.get("pinecone_namespace", "")
    if not index_name:
        return {"status": "skipped", "reason": "no index configured"}

    try:
        api_key = _choose_pinecone_api_key(index_name)
    except ValueError as e:
        return {"status": "error", "reason": str(e)}

    try:
        host = _resolve_index_host(index_name, api_key)
    except ValueError as e:
        return {"status": "error", "reason": str(e)}

    try:
        vector = _embed_query("recovery workflow")
    except (ValueError, KeyError) as e:
        return {"status": "error", "reason": f"embedding failed: {e}"}

    query_payload = {
        "vector": vector,
        "topK": 3,
        "includeMetadata": True,
    }
    if namespace:
        query_payload["namespace"] = namespace

    try:
        result = pc_http_json(
            "POST",
            f"https://{host}/query",
            headers={"Api-Key": api_key},
            payload=query_payload,
        )
    except ValueError as e:
        return {"status": "error", "reason": str(e)}

    matches = result.get("matches", [])
    if not matches:
        return {"status": "warning", "reason": "no results", "count": 0}

    top_score = max(m.get("score", 0) for m in matches)
    snippets = []
    for m in matches:
        meta = m.get("metadata", {})
        text = str(meta.get("text") or meta.get("content") or meta.get("title") or m.get("id", ""))[:80]
        snippets.append({"id": m.get("id"), "score": round(m.get("score", 0), 3), "text": text})

    return {"status": "verified", "count": len(matches), "top_score": round(top_score, 3), "snippets": snippets}


# ── Phase 4: Tenant-Pinecone mapping ────────────────────────────────

def write_pinecone_map(users: list[dict], runtime_home: Path, force: bool, dry_run: bool) -> None:
    map_path = runtime_home / "tenant_pinecone_map.json"
    existing = {}
    if map_path.exists():
        try:
            existing = json.loads(map_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    for u in users:
        tid = u.get("tenant_id")
        idx = u.get("pinecone_index")
        ns = u.get("pinecone_namespace", "")
        if not tid or not idx:
            continue
        if tid in existing and not force:
            continue
        existing[tid] = {"index": idx, "namespace": ns}

    if dry_run:
        print(f"\nWould write tenant_pinecone_map.json with {len(existing)} entries")
        return

    map_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {map_path} ({len(existing)} entries)")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Onboard SAI Recovery users into Bomba SR")
    parser.add_argument("--config", required=True, help="Path to user config JSON")
    parser.add_argument("--runtime-home", default=".runtime", help="Runtime home directory")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing Pinecone mappings")
    parser.add_argument("--skip-supabase", action="store_true", help="Skip Supabase memory pull")
    parser.add_argument("--skip-pinecone", action="store_true", help="Skip Pinecone verification")
    args = parser.parse_args()

    # Load .env
    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    runtime_home = Path(args.runtime_home)
    os.environ.setdefault("BOMBA_RUNTIME_HOME", str(runtime_home))

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    users = config.get("users", [])
    if not users:
        print("No users in config file.")
        return

    from bomba_sr.storage.factory import create_shared_db
    mc_db = create_shared_db()

    # Ensure MC schema exists (DashboardService does this, but we might not have it)
    from bomba_sr.dashboard.service import DashboardService
    from bomba_sr.runtime.bridge import RuntimeBridge
    bridge = RuntimeBridge()
    svc = DashboardService(db=mc_db, bridge=bridge)

    results = []

    for u in users:
        email = u["email"]
        print(f"\n{'='*60}")
        print(f"User: {email}")
        print(f"{'='*60}")
        result = {"email": email}

        # Phase 1: Account
        print("  [1] Account creation...")
        status = create_account(mc_db, u, runtime_home, args.dry_run)
        result["account"] = status
        print(f"    {status}")

        # Phase 2: Supabase
        if args.skip_supabase or not u.get("supabase_sister"):
            result["supabase"] = "skipped"
            print("  [2] Supabase: skipped")
        else:
            print("  [2] Supabase memory pull...")
            count = pull_supabase(u, runtime_home, args.dry_run)
            result["supabase"] = f"{count} records imported"
            print(f"    {count} records imported")

        # Phase 3: Pinecone
        if args.skip_pinecone or not u.get("pinecone_index"):
            result["pinecone"] = "skipped"
            print("  [3] Pinecone: skipped")
        elif args.dry_run:
            result["pinecone"] = "would verify"
            print("  [3] Pinecone: would verify")
        else:
            print("  [3] Pinecone verification...")
            pc_result = verify_pinecone(u)
            if pc_result["status"] == "verified":
                result["pinecone"] = f"verified ({pc_result['count']} results, top score {pc_result['top_score']})"
                for s in pc_result.get("snippets", []):
                    print(f"    {s['id']}: score={s['score']} — {s['text']}")
            elif pc_result["status"] == "warning":
                result["pinecone"] = f"warning: {pc_result['reason']}"
            else:
                result["pinecone"] = f"error: {pc_result['reason']}"
            print(f"    {result['pinecone']}")

        results.append(result)

    # Phase 4: Pinecone mapping
    write_pinecone_map(users, runtime_home, args.force, args.dry_run)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"\nUser: {r['email']}")
        print(f"  Account:  {r['account']}")
        print(f"  Supabase: {r['supabase']}")
        print(f"  Pinecone: {r['pinecone']}")


if __name__ == "__main__":
    main()
