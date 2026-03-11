# Colosseum API Server

REST API for the Colosseum evolution system - being management, stats, judge performance, and tournament control.

**Port:** 3341

## Quick Start

```bash
./start.sh
# Or manually:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

## Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /evolution/status` - Current evolution status (generations, activity, latest tournament)

### Beings
- `GET /beings` - List all beings with scores
  - Query params: `limit`, `offset`, `generation`, `min_score`, `sort_by`
- `GET /beings/top/{n}` - Top N beings by mastery score
- `GET /beings/{name}` - Specific being details (by name or ID)

### Statistics
- `GET /stats` - Overall colosseum statistics
- `GET /judges` - Judge performance metrics

### Rounds
- `GET /rounds/recent` - Recent round results
  - Query params: `limit`, `being_id`, `tournament_id`

### Tournaments
- `GET /tournaments` - List tournaments
- `GET /tournaments/{id}` - Tournament details with participant stats
- `POST /tournament/start` - Start new tournament
  ```json
  {"mode": "standard", "beings_count": 10, "config": {}}
  ```

## Example Usage

```bash
# Health check
curl http://localhost:3341/health

# Top 10 beings
curl http://localhost:3341/beings/top/10

# Overall stats
curl http://localhost:3341/stats

# Evolution status
curl http://localhost:3341/evolution/status

# Start tournament
curl -X POST http://localhost:3341/tournament/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "standard"}'
```

## Database

Uses SQLite database at `~/Projects/colosseum/colosseum.db`
