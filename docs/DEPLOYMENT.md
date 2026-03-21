# Production deployment

## HTTPS (required)

The runtime server binds plain HTTP. For production, put Caddy in front
for automatic HTTPS via Let's Encrypt.

1. Install Caddy: https://caddyserver.com/docs/install
2. Edit `Caddyfile` — replace `bomba.acti.ai` with your domain
3. Run: `caddy run --config Caddyfile`

## Server binding

Start the runtime on all interfaces (required for remote access):

```bash
PYTHONPATH=src python scripts/run_api_server.py --host 0.0.0.0 --port 8787
```

For multi-process concurrency (recommended for production):

```bash
PYTHONPATH=src python scripts/run_api_server.py --host 0.0.0.0 --port 8787 --workers 4
```

## Database

The shared Mission Control database (users, sessions, tasks, messages) supports
both SQLite and PostgreSQL. Per-tenant databases always use SQLite.

**PostgreSQL (recommended for production):**

```bash
# Start Postgres
docker compose up -d

# Add to .env
BOMBA_POSTGRES_DSN=postgresql://bomba:bomba_secure_2026@localhost:5432/bomba_mc

# If upgrading from SQLite, migrate existing data
PYTHONPATH=src python scripts/migrate_sqlite_to_postgres.py \
  --sqlite .runtime/bomba_runtime.db \
  --postgres "postgresql://bomba:bomba_secure_2026@localhost:5432/bomba_mc"

# Verify
PYTHONPATH=src python scripts/migrate_sqlite_to_postgres.py \
  --sqlite .runtime/bomba_runtime.db \
  --postgres "postgresql://bomba:bomba_secure_2026@localhost:5432/bomba_mc" \
  --verify-only
```

**SQLite (default, no setup needed):**

Omit `BOMBA_POSTGRES_DSN` from `.env` and the server uses
`.runtime/bomba_runtime.db` automatically. No Docker required.

## Preflight check

Verify the system is ready before launch:

```bash
PYTHONPATH=src python scripts/preflight_check.py
```
