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
PYTHONPATH=src python scripts/run_runtime_server.py --host 0.0.0.0 --port 8787
```
