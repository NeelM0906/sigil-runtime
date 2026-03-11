# SAI Automation Servers 🔥

## Quick Start

```bash
# Start all servers
./start-all.sh

# Check status
./start-all.sh status

# Stop all
./start-all.sh stop

# Restart all
./start-all.sh restart
```

## Auto-Start on Boot

```bash
./install-launchd.sh
```

## Running Servers

| Server | Port | Directory | Description |
|--------|------|-----------|-------------|
| **7 Levers** | 3340 | `7levers-server/` | Metrics aggregation from Bland.ai, CRM, ElevenLabs |
| **Colosseum** | 3341 | `colosseum-api/` | Being management, evolution stats, judge monitoring |
| **Reporting** | 3344 | `reporting-server/` | Bi-hourly reports, 7 levers tracking, best calls |

## Also Available (separate)
- **Voice Server** (port 3334) - Twilio + Deepgram + ElevenLabs + OpenAI
- **ElevenLabs Webhook** - Transcript capture

## Planned Servers

### Knowledge Sync Server (port 3342)
- Continuous Pinecone sync
- Transcript → Translator pipeline
- Memory consolidation

### Call Routing Proxy (port 3343)
- Routes calls to best available being
- Load balancing across beings
- Real-time performance routing

## Logs

All logs go to `~/Projects/automation-logs/`:
- `7_levers.log` - 7 Levers server logs
- `colosseum.log` - Colosseum API logs
- `reporting.log` - Reporting server logs
- `startup-*.log` - Startup script logs
- `launchd-*.log` - launchd output (if using auto-start)

## Health Checks

```bash
curl http://localhost:3340/health  # 7 Levers
curl http://localhost:3341/health  # Colosseum
curl http://localhost:3344/health  # Reporting
```

## Architecture
All servers:
- Run as background daemons via nohup
- Python/FastAPI with virtual environments
- Health check endpoints at /health
- Auto-start via launchd (optional)
