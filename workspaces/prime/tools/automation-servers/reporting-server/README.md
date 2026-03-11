# Reporting Aggregator Proxy Server

Bi-hourly reporting server for Sean — tracks 7 levers across 3 companies, surfaces best calls for grading.

## Quick Start

```bash
cd ~/.openclaw/workspace/tools/automation-servers/reporting-server

# Create virtual environment (first time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run server
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 3344 --reload
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /report/headline` | Quick bi-hourly summary |
| `GET /report/detailed` | Full daily report with drill-downs |
| `GET /report/best-calls` | Top calls for Sean to review |
| `GET /report/lever/{id}` | Deep drill-down into specific lever |
| `GET /report/being/{name}` | Activity for specific ACT-I being |
| `POST /report/question` | Submit question needing human input |

## Query Parameters

### /report/headline
- `company` — Filter by company (ACT-I, Unblinded, Callagy Recovery)
- `lever` — Filter by lever (0.25, 0.5, 1-7)

### /report/detailed
- `date` — Date (YYYY-MM-DD), defaults to today
- `company` — Filter by company
- `section` — Section filter: levers, beings, colosseum, llm

### /report/best-calls
- `company` — Filter by company
- `lever` — Filter by lever
- `limit` — Calls per company/lever (default 3)

## The 7 Levers

| Lever | Name |
|-------|------|
| 0.25 | Sourcing Data |
| 0.5 | Shared Experiences (Process Mastery) |
| 1 | Ecosystem Mergers |
| 2 | Speaking Engagements & Marketing |
| 3 | Sales |
| 4 | Referrals |
| 5 | Direct Outreach |
| 6 | Advertising |
| 7 | Content/PR |

## Companies

- **ACT-I** — Main entity
- **Unblinded** — Media/content
- **Callagy Recovery** — Legal recovery

## ACT-I Beings

- **Athena** — Ecosystem merging, sales, actualizing
- **Milo** — Aiko's being
- **Mira** — User companion
- **Callie** — Conversational mastery

## Data Sources

### ElevenLabs
- Fetches call transcripts and analytics
- Groups calls by being and lever
- Scores calls for review prioritization

### Pinecone
- Primary account: athenacontextualmemory, uicontextualmemory, ublib2
- Strata account: ultimatestratabrain, suritrial, oracleinfluencemastery

## Example Usage

```bash
# Quick health check
curl http://localhost:3344/health

# Get bi-hourly headline
curl http://localhost:3344/report/headline

# Get headline for specific company
curl "http://localhost:3344/report/headline?company=ACT-I"

# Get detailed daily report
curl http://localhost:3344/report/detailed

# Get best calls for Sean
curl http://localhost:3344/report/best-calls

# Drill into specific lever
curl http://localhost:3344/report/lever/3

# Get Athena's activity
curl http://localhost:3344/report/being/Athena

# Submit a question for Sean
curl -X POST "http://localhost:3344/report/question?question=Should%20we%20expand%20Athena%27s%20capabilities%3F&for_person=Sean"
```

## Reference

Based on: `~/.openclaw/workspace/memory/bi-hourly-questionnaire-v2.md`

Port: **3344**
