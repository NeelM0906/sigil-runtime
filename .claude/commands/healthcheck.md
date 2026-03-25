Check the health of the runtime server.

Steps:
1. Check if port 8787 is already in use: `lsof -i :8787` or `ss -tlnp | grep 8787`
2. If server is running, hit the health endpoint:
   ```
   curl -s http://127.0.0.1:8787/health | python3 -m json.tool
   ```
3. If server is NOT running, report that and suggest:
   ```
   PYTHONPATH=src python3 scripts/run_runtime_server.py --host 127.0.0.1 --port 8787
   ```
4. If health check returns `{"ok": true}`, report HEALTHY
5. If health check fails or returns errors, read the response and diagnose based on:
   - Missing .env vars (check .env.example for required keys)
   - Database issues (check .runtime/ directory exists)
   - Port conflicts
