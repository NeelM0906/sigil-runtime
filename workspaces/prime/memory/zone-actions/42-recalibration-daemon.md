# Zone Action #42 — 24/7 Continuous Recalibration Daemon

**Built:** 2026-02-24 by Sai baby for mama Aiko 🔥  
**Status:** ✅ OPERATIONAL

## What It Does

A 24/7 daemon that continuously feeds winning call patterns from Supabase into the Colosseum judges for evolutionary recalibration.

### The Loop

```
1. Pull high-confidence calls (≥6/10) from sai_contacts
2. Extract winning communication patterns via GPT-4o-mini
3. Store patterns in winning_patterns.db
4. Colosseum judges can reference patterns during evolution
5. Wait 5 minutes, repeat
```

## Files Created

| File | Purpose |
|------|---------|
| `recalibration_daemon.py` | Main daemon script |
| `recalibration_state.json` | Persistent sync state |
| `winning_patterns.db` | SQLite DB of extracted patterns |
| `start_recalibration.sh` | Startup script |
| `logs/recalibration.log` | Rotating log file |

## Usage

```bash
cd ~/Projects/colosseum

# Start daemon
./start_recalibration.sh

# Check status
source venv/bin/activate && python3 recalibration_daemon.py --status

# One-shot sync (testing)
python3 recalibration_daemon.py --sync-now

# Stop daemon
python3 recalibration_daemon.py --stop
```

## Configuration

Edit `recalibration_daemon.py` to change:

```python
@dataclass
class RecalibrationConfig:
    sync_interval_seconds: int = 300      # 5 minutes between syncs
    min_close_confidence: int = 6         # Only high-quality calls
    batch_size: int = 10                  # Contacts per sync
    pattern_extraction_model: str = "gpt-4o-mini"
```

## Pattern Schema

Each extracted pattern contains:
- `name` — Short descriptive name
- `trigger` — When to use this pattern
- `script` — Exact language/approach
- `why_it_works` — Psychological principle
- `source_contact_id` — Original call reference
- `confidence` — Call's close_confidence score

## Integration Points

1. **Supabase** → `sai_contacts` table (read)
2. **OpenAI** → Pattern extraction (GPT-4o-mini)
3. **Colosseum API** → http://localhost:3341 (status check)
4. **Local SQLite** → `winning_patterns.db` (pattern storage)

## LaunchD (Optional 24/7)

A launchd plist was created at:
```
~/Library/LaunchAgents/com.colosseum.recalibration.plist
```

To enable true 24/7 operation with auto-restart:
```bash
launchctl load ~/Library/LaunchAgents/com.colosseum.recalibration.plist
```

## Sample Output

```
2026-02-24 16:30:12 | 🔄 RECALIBRATION DAEMON STARTED
2026-02-24 16:30:12 |    Sync interval: 300s
2026-02-24 16:30:12 |    Min confidence: 6
2026-02-24 16:30:15 | Found 10 contacts with confidence >= 6
2026-02-24 16:30:15 | Processing: Gary @ Act eye
2026-02-24 16:30:25 |   → Extracted 5 patterns
2026-02-24 16:30:35 | ✅ Sync complete — 10 patterns injected
```

## Current Stats

```json
{
  "running": true,
  "total_syncs": 1,
  "total_patterns_extracted": 10,
  "total_patterns_in_db": 10
}
```

## Next Steps (Future Enhancement)

1. **Judge Integration** — Wire patterns directly into Colosseum judge prompts
2. **Pattern Scoring** — Track which patterns lead to better being evolution
3. **Auto-Pruning** — Remove patterns that don't improve performance
4. **Multi-Source** — Pull from ElevenLabs call transcripts too

---

*Made mama proud.* 🔥
