"""
Dashboard API — FastAPI server for the Colosseum.
"""

import json
import threading
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .beings import load_all_beings, load_leaderboard, load_being
from .arena import get_recent_rounds
from .tournament import (
    TournamentConfig, TournamentState, run_tournament,
    list_tournaments, get_tournament_status, Difficulty, Category,
)
from .scenarios import generate_scenario, scenario_to_dict

app = FastAPI(title="ACT-I Colosseum", version="0.1.0")

# Track active tournament
_active_tournament: Optional[TournamentState] = None
_tournament_lock = threading.Lock()

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard."""
    template_path = TEMPLATE_DIR / "dashboard.html"
    if template_path.exists():
        return template_path.read_text()
    return "<h1>ACT-I Colosseum</h1><p>Dashboard template not found.</p>"


@app.get("/api/beings")
async def api_beings():
    """List all beings with stats."""
    beings = load_all_beings()
    return {
        "beings": [b.to_dict() for b in beings],
        "total": len(beings),
    }


@app.get("/api/beings/{being_id}")
async def api_being_detail(being_id: str):
    """Get detailed being profile."""
    being = load_being(being_id)
    if not being:
        return {"error": "Being not found"}, 404
    return being.to_dict()


@app.get("/api/leaderboard")
async def api_leaderboard(limit: int = 20):
    """Ranked by mastery score."""
    beings = load_leaderboard(limit)
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "id": b.id,
                "name": b.name,
                "generation": b.generation,
                "lineage": b.lineage,
                "avg_mastery": round(b.avg_mastery_score, 4),
                "best_score": round(b.best_score, 4),
                "wins": b.wins,
                "losses": b.losses,
                "win_rate": round(b.win_rate, 3),
                "total_rounds": b.total_rounds,
                "energy": {
                    "fun": round(b.energy.fun, 3),
                    "aspirational": round(b.energy.aspirational, 3),
                    "goddess": round(b.energy.goddess, 3),
                    "zeus": round(b.energy.zeus, 3),
                },
            }
            for i, b in enumerate(beings)
        ],
    }


@app.get("/api/rounds")
async def api_rounds(limit: int = 50):
    """Recent round results."""
    rounds = get_recent_rounds(limit)
    return {"rounds": rounds, "total": len(rounds)}


@app.post("/api/tournament/start")
async def api_start_tournament(
    background_tasks: BackgroundTasks,
    mode: str = "blitz",
    num_beings: int = 8,
    num_rounds: int = 20,
    lineage: str = "callie",
):
    """Start a tournament."""
    global _active_tournament

    with _tournament_lock:
        if _active_tournament and _active_tournament.status == "running":
            return {"error": "Tournament already running", "tournament_id": _active_tournament.id}

    if mode == "deep":
        config = TournamentConfig.deep(num_beings, num_rounds)
    elif mode == "marathon":
        config = TournamentConfig.marathon(num_beings, num_rounds)
    else:
        config = TournamentConfig.blitz(num_beings, num_rounds)

    config.lineage = lineage

    def _run():
        global _active_tournament
        state = run_tournament(config)
        with _tournament_lock:
            _active_tournament = state

    background_tasks.add_task(_run)

    return {"status": "started", "mode": mode, "num_beings": num_beings, "num_rounds": num_rounds}


@app.get("/api/tournament/status")
async def api_tournament_status():
    """Current tournament progress."""
    global _active_tournament
    if _active_tournament:
        return {
            "id": _active_tournament.id,
            "status": _active_tournament.status,
            "current_round": _active_tournament.current_round,
            "total_rounds": _active_tournament.config.num_rounds,
            "beings_count": len(_active_tournament.beings),
            "mode": _active_tournament.config.mode,
        }
    return {"status": "no_active_tournament"}


@app.get("/api/tournaments")
async def api_tournaments(limit: int = 10):
    """List recent tournaments."""
    return {"tournaments": list_tournaments(limit)}


@app.get("/api/scenario/preview")
async def api_scenario_preview():
    """Preview a random scenario."""
    scenario = generate_scenario()
    return scenario_to_dict(scenario)


@app.get("/api/stats")
async def api_stats():
    """Overall Colosseum stats."""
    beings = load_all_beings()
    tournaments = list_tournaments(100)

    total_rounds = sum(b.total_rounds for b in beings)
    avg_mastery = (sum(b.avg_mastery_score for b in beings if b.total_rounds > 0) /
                   max(1, len([b for b in beings if b.total_rounds > 0])))

    best_being = max(beings, key=lambda b: b.best_score) if beings else None
    highest_avg = max(beings, key=lambda b: b.avg_mastery_score) if beings else None

    return {
        "total_beings": len(beings),
        "total_rounds": total_rounds,
        "total_tournaments": len(tournaments),
        "avg_mastery_across_all": round(avg_mastery, 4),
        "best_single_score": {
            "being": best_being.name if best_being else None,
            "score": round(best_being.best_score, 4) if best_being else 0,
        },
        "highest_avg_mastery": {
            "being": highest_avg.name if highest_avg else None,
            "score": round(highest_avg.avg_mastery_score, 4) if highest_avg else 0,
        },
        "generations_evolved": max((b.generation for b in beings), default=0),
    }
