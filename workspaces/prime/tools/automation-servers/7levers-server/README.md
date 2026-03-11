# 7 Levers Metrics Proxy Server

A FastAPI server that aggregates data from Bland.ai, ElevenLabs, and Zoom to provide lever-based business metrics for ACT-I, Unblinded, and Callagy Recovery.

## Quick Start

```bash
cd ~/.openclaw/workspace/tools/automation-servers/7levers-server
./start.sh
```

Or manually:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

Server runs on **port 3340**.

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /stats` - Aggregate stats from all data sources
- `GET /companies` - List tracked companies
- `GET /levers` - List all lever definitions

### Company Metrics
- `GET /metrics/{company}` - All lever metrics for a company
- `GET /metrics/{company}/lever/{lever_id}` - Specific lever metric
- `GET /drill-down/{company}/lever/{lever_id}` - Detailed data points (50-100)
- `GET /report/{company}` - Comprehensive bi-hourly report

### Best Calls (9.99 Quality)
- `GET /best-calls` - Surface exceptional calls for study
- `GET /call/{call_id}` - Full call details with quality score

### Cache Management
- `POST /cache/clear` - Clear metrics cache

## Levers

| ID | Name | Description |
|----|------|-------------|
| 0.25 | Awareness | Market awareness, brand recognition |
| 0.5 | Interest | Lead generation, opt-ins |
| 1 | Traffic | Inbound traffic, visitors |
| 2 | Opt-in Rate | Conversion from visitor to lead |
| 3 | Buyer Rate | Conversion from lead to buyer |
| 4 | Units per Buyer | Average items purchased |
| 5 | Revenue per Unit | Average revenue per sale |
| 6 | Profit Margin | Profit percentage |
| 7 | Frequency | Purchase frequency / retention |

## Companies

- `acti` - ACT-I
- `unblinded` - Unblinded
- `callagy_recovery` - Callagy Recovery

## Examples

```bash
# Get all metrics for ACT-I (last 30 days)
curl http://localhost:3340/metrics/acti

# Get specific lever
curl http://localhost:3340/metrics/acti/lever/3

# Drill down into lever 3 with 100 data points
curl "http://localhost:3340/drill-down/acti/lever/3?limit=100"

# Find best calls (score >= 9.0)
curl "http://localhost:3340/best-calls?min_score=9.0"

# Generate bi-hourly report
curl http://localhost:3340/report/acti

# Force cache refresh
curl "http://localhost:3340/metrics/acti?refresh=true"
```

## Install as launchd Service (macOS)

```bash
# Copy plist to LaunchAgents
cp com.openclaw.7levers.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.openclaw.7levers.plist

# Check status
launchctl list | grep 7levers

# View logs
tail -f /tmp/7levers-server.log
```

## Configuration

API keys are loaded from `~/.openclaw/.env`:
- `BLAND_API_KEY` - Bland.ai API key (287K calls)
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` - Zoom OAuth

## Call Quality Scoring

Calls are scored 0-10 based on:
- Duration (ideal: 5-15 minutes)
- Completion status
- Transcript richness
- Sentiment indicators

**9.99 calls** are exceptional - these are the ones worth studying and replicating.

## Cache

- Default TTL: 2 hours (7200 seconds)
- Automatically warms up on startup
- Use `?refresh=true` to bypass cache
