#!/usr/bin/env python3
"""Pre-launch checklist — verifies the system is ready for multi-user deployment."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

# Load .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[7:].strip()
        if "=" in raw:
            k, v = raw.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k:
                os.environ.setdefault(k, v)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_HOME = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))

passes: list[str] = []
warnings: list[str] = []
blockers: list[str] = []


def ok(msg: str) -> None:
    passes.append(msg)
    print(f"  \033[32m✓\033[0m {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  \033[33m⚠\033[0m {msg}")


def fail(msg: str) -> None:
    blockers.append(msg)
    print(f"  \033[31m✗\033[0m {msg}")


# ── 1. Python dependencies ──────────────────────────────────────────
print("\n\033[1m[1] Python dependencies\033[0m")
for mod, required in [("fastapi", True), ("uvicorn", True), ("bcrypt", True), ("psycopg", False)]:
    try:
        __import__(mod)
        ok(f"{mod} installed")
    except ImportError:
        if required:
            fail(f"{mod} MISSING (run: pip install {mod})")
        else:
            warn(f"{mod} not installed (SQLite mode)")

# ── 2. Environment variables ────────────────────────────────────────
print("\n\033[1m[2] Environment variables\033[0m")

or_key = os.getenv("OPENROUTER_API_KEY", "")
if or_key and not or_key.startswith("<") and or_key != "your-openrouter-key":
    ok("OPENROUTER_API_KEY configured")
else:
    fail("OPENROUTER_API_KEY missing or placeholder")

for var, label in [
    ("SUPABASE_URL", "Supabase"),
    ("SUPABASE_SERVICE_KEY", "Supabase service key"),
    ("PINECONE_API_KEY", "Pinecone"),
]:
    val = os.getenv(var, "").strip()
    if val:
        ok(f"{var} set")
    else:
        warn(f"{var} not set ({label} features disabled)")

pg_dsn = os.getenv("BOMBA_POSTGRES_DSN", "").strip()
if pg_dsn:
    ok(f"BOMBA_POSTGRES_DSN set (Postgres mode)")
else:
    warn("BOMBA_POSTGRES_DSN not set (SQLite mode)")

cors = os.getenv("BOMBA_CORS_ALLOWED_ORIGINS", "").strip()
if cors:
    ok(f"BOMBA_CORS_ALLOWED_ORIGINS: {cors[:60]}")
else:
    warn("BOMBA_CORS_ALLOWED_ORIGINS not set (localhost defaults)")

# ── 3. Database ─────────────────────────────────────────────────────
print("\n\033[1m[3] Database\033[0m")
db = None
db_type = "unknown"
try:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from bomba_sr.storage.factory import create_shared_db
    db = create_shared_db()
    db_type = type(db).__name__
    ok(f"Shared DB connectable ({db_type})")

    user_count = db.execute("SELECT COUNT(*) as c FROM mc_users").fetchone()["c"]
    if user_count > 0:
        ok(f"{user_count} users in mc_users")
    else:
        warn("mc_users is empty (no accounts created yet)")

    db.execute("SELECT 1 FROM mc_sessions_auth LIMIT 0")
    ok("mc_sessions_auth table exists")

    db.execute("SELECT 1 FROM tool_audit_log LIMIT 0")
    ok("tool_audit_log table exists")
except Exception as e:
    fail(f"Database error: {e}")

# ── 4. Tenant system ────────────────────────────────────────────────
print("\n\033[1m[4] Tenant system\033[0m")
if RUNTIME_HOME.is_dir():
    ok(f".runtime directory exists ({RUNTIME_HOME})")
else:
    fail(f".runtime directory missing ({RUNTIME_HOME})")

tenants_dir = RUNTIME_HOME / "tenants"
if tenants_dir.is_dir():
    tenant_dirs = [d.name for d in tenants_dir.iterdir() if d.is_dir()]
    if tenant_dirs:
        ok(f"{len(tenant_dirs)} tenant directories: {', '.join(sorted(tenant_dirs)[:5])}{'...' if len(tenant_dirs) > 5 else ''}")
    else:
        warn("No tenant directories yet (created on first login)")
else:
    warn("tenants/ directory missing (created on first registration)")

# ── 5. Pinecone ─────────────────────────────────────────────────────
print("\n\033[1m[5] Pinecone routing\033[0m")
map_path = RUNTIME_HOME / "tenant_pinecone_map.json"
if map_path.exists():
    try:
        pc_map = json.loads(map_path.read_text(encoding="utf-8"))
        ok(f"tenant_pinecone_map.json: {len(pc_map)} entries")
        for tid, cfg in list(pc_map.items())[:5]:
            print(f"       {tid} → {cfg.get('index', '?')}/{cfg.get('namespace', '?')}")
    except Exception as e:
        warn(f"tenant_pinecone_map.json parse error: {e}")
else:
    warn("tenant_pinecone_map.json not found (run migrate_user_data.py)")

pc_key = os.getenv("PINECONE_API_KEY", "").strip()
if pc_key:
    try:
        from bomba_sr.tools.builtin_pinecone import _list_indexes_with_cache, _index_records
        payload = _list_indexes_with_cache(pc_key)
        indexes = _index_records(payload)
        ok(f"Pinecone API: {len(indexes)} indexes accessible")
    except Exception as e:
        warn(f"Pinecone API error: {e}")

# ── 6. Frontend ─────────────────────────────────────────────────────
print("\n\033[1m[6] Frontend\033[0m")
mc_dir = PROJECT_ROOT / "mission-control"
if (mc_dir / "node_modules").is_dir():
    ok("mission-control/node_modules present")
else:
    fail("mission-control/node_modules missing (run: cd mission-control && npm install)")

if (mc_dir / "dist").is_dir():
    ok("mission-control/dist present (production build)")
else:
    warn("mission-control/dist missing (run: cd mission-control && npx vite build)")

# ── 7. Server port ──────────────────────────────────────────────────
print("\n\033[1m[7] Server\033[0m")
port = 8787
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    if result == 0:
        # Port in use — find PID
        try:
            out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
            warn(f"Port {port} in use by PID {out.split()[0]}")
        except Exception:
            warn(f"Port {port} in use")
    else:
        ok(f"Port {port} available")
except Exception:
    ok(f"Port {port} available")

# ── Summary ─────────────────────────────────────────────────────────
print(f"\n\033[1m{'='*50}\033[0m")
print(f"\033[1mSummary\033[0m: {len(passes)} passed, {len(warnings)} warnings, {len(blockers)} blockers")

if blockers:
    print(f"\n\033[31mNOT READY — {len(blockers)} blocker(s):\033[0m")
    for b in blockers:
        print(f"  \033[31m✗\033[0m {b}")
elif warnings:
    print(f"\n\033[32mREADY\033[0m ({len(warnings)} warning{'s' if len(warnings) != 1 else ''})")
else:
    print(f"\n\033[32mREADY — all checks passed\033[0m")

sys.exit(1 if blockers else 0)
