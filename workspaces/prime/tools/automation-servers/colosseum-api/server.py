#!/usr/bin/env python3
"""
Colosseum API Proxy Server
REST API for managing beings, evolution stats, judge performance, and tournament control.
Port: 3341
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configuration
DB_PATH = Path.home() / "Projects" / "colosseum" / "colosseum.db"
PORT = 3341

app = FastAPI(
    title="Colosseum API",
    description="REST API for the Colosseum evolution system - being management, stats, and tournament control",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Database Helpers ---

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    """Convert sqlite3.Row to dict, parsing JSON fields."""
    if row is None:
        return None
    d = dict(row)
    # Parse JSON fields
    json_fields = ['energy_json', 'traits_json', 'strengths_json', 'weaknesses_json', 
                   'parent_ids_json', 'scores_json', 'scenario_json', 'config_json',
                   'variables_json', 'analysis_json', 'metadata_json', 'detailed_metrics_json']
    for field in json_fields:
        if field in d and d[field]:
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# --- Pydantic Models ---

class TournamentStartRequest(BaseModel):
    mode: str = "standard"
    beings_count: Optional[int] = None
    config: Optional[dict] = None


class BeingResponse(BaseModel):
    id: str
    name: str
    generation: int
    lineage: Optional[str]
    wins: int
    losses: int
    total_rounds: int
    avg_mastery_score: float
    best_score: float
    win_rate: float
    created_at: str


# --- Health & Status Endpoints ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.get("/evolution/status")
async def evolution_status():
    """Get current evolution status - generation stats, active beings, recent activity."""
    with get_db() as conn:
        # Generation distribution
        gen_stats = conn.execute("""
            SELECT generation, COUNT(*) as count, AVG(avg_mastery_score) as avg_score
            FROM beings
            GROUP BY generation
            ORDER BY generation DESC
            LIMIT 10
        """).fetchall()
        
        # Recent tournament
        recent_tournament = conn.execute("""
            SELECT * FROM tournaments
            ORDER BY started_at DESC
            LIMIT 1
        """).fetchone()
        
        # Total stats
        totals = conn.execute("""
            SELECT 
                COUNT(*) as total_beings,
                MAX(generation) as latest_generation,
                AVG(avg_mastery_score) as global_avg_score,
                MAX(best_score) as all_time_best
            FROM beings
        """).fetchone()
        
        # Recent activity (rounds in last 24h)
        recent_rounds = conn.execute("""
            SELECT COUNT(*) as count
            FROM rounds
            WHERE created_at > datetime('now', '-24 hours')
        """).fetchone()
        
        return {
            "total_beings": totals["total_beings"],
            "latest_generation": totals["latest_generation"],
            "global_avg_score": round(totals["global_avg_score"] or 0, 3),
            "all_time_best_score": totals["all_time_best"],
            "recent_rounds_24h": recent_rounds["count"],
            "generation_breakdown": [
                {"generation": r["generation"], "count": r["count"], "avg_score": round(r["avg_score"] or 0, 3)}
                for r in gen_stats
            ],
            "current_tournament": row_to_dict(recent_tournament) if recent_tournament else None,
            "timestamp": datetime.now().isoformat()
        }


# --- Being Endpoints ---

@app.get("/beings")
async def list_beings(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    generation: Optional[int] = None,
    min_score: Optional[float] = None,
    sort_by: str = Query("avg_mastery_score", enum=["avg_mastery_score", "wins", "total_rounds", "created_at", "best_score"])
):
    """List all beings with scores and stats."""
    with get_db() as conn:
        query = "SELECT * FROM beings WHERE 1=1"
        params = []
        
        if generation is not None:
            query += " AND generation = ?"
            params.append(generation)
        
        if min_score is not None:
            query += " AND avg_mastery_score >= ?"
            params.append(min_score)
        
        query += f" ORDER BY {sort_by} DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        beings = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
        
        results = []
        for b in beings:
            bd = row_to_dict(b)
            bd["win_rate"] = round(bd["wins"] / bd["total_rounds"], 3) if bd["total_rounds"] > 0 else 0
            results.append(bd)
        
        return {
            "beings": results,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@app.get("/beings/top/{n}")
async def top_beings(n: int):
    """Get top N beings by mastery score."""
    if n < 1 or n > 100:
        raise HTTPException(status_code=400, detail="n must be between 1 and 100")
    
    with get_db() as conn:
        beings = conn.execute("""
            SELECT * FROM beings
            ORDER BY avg_mastery_score DESC
            LIMIT ?
        """, [n]).fetchall()
        
        results = []
        for i, b in enumerate(beings, 1):
            bd = row_to_dict(b)
            bd["rank"] = i
            bd["win_rate"] = round(bd["wins"] / bd["total_rounds"], 3) if bd["total_rounds"] > 0 else 0
            results.append(bd)
        
        return {"top_beings": results, "count": len(results)}


@app.get("/beings/{name}")
async def get_being(name: str):
    """Get specific being details by name or ID."""
    with get_db() as conn:
        # Try by name first, then by id
        being = conn.execute(
            "SELECT * FROM beings WHERE name = ? OR id = ?",
            [name, name]
        ).fetchone()
        
        if not being:
            raise HTTPException(status_code=404, detail=f"Being '{name}' not found")
        
        bd = row_to_dict(being)
        bd["win_rate"] = round(bd["wins"] / bd["total_rounds"], 3) if bd["total_rounds"] > 0 else 0
        
        # Get recent rounds
        recent_rounds = conn.execute("""
            SELECT id, scenario_id, mastery_score, won, created_at
            FROM rounds
            WHERE being_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, [bd["id"]]).fetchall()
        
        bd["recent_rounds"] = [row_to_dict(r) for r in recent_rounds]
        
        return bd


# --- Statistics Endpoints ---

@app.get("/stats")
async def overall_stats():
    """Overall colosseum statistics."""
    with get_db() as conn:
        # Being stats
        being_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_beings,
                MAX(generation) as max_generation,
                AVG(avg_mastery_score) as avg_mastery,
                MAX(best_score) as best_ever_score,
                SUM(wins) as total_wins,
                SUM(total_rounds) as total_rounds_played
            FROM beings
        """).fetchone()
        
        # Tournament stats
        tournament_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_tournaments,
                SUM(total_rounds) as tournament_rounds,
                COUNT(CASE WHEN status = 'running' THEN 1 END) as active_tournaments
            FROM tournaments
        """).fetchone()
        
        # Round stats
        round_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_rounds,
                AVG(mastery_score) as avg_round_score,
                MAX(mastery_score) as max_round_score
            FROM rounds
        """).fetchone()
        
        # Top performer
        top_being = conn.execute("""
            SELECT name, avg_mastery_score, wins, total_rounds
            FROM beings
            ORDER BY avg_mastery_score DESC
            LIMIT 1
        """).fetchone()
        
        # Score distribution
        score_distribution = conn.execute("""
            SELECT 
                CASE 
                    WHEN avg_mastery_score >= 0.9 THEN 'elite (0.9+)'
                    WHEN avg_mastery_score >= 0.7 THEN 'strong (0.7-0.9)'
                    WHEN avg_mastery_score >= 0.5 THEN 'average (0.5-0.7)'
                    ELSE 'developing (<0.5)'
                END as tier,
                COUNT(*) as count
            FROM beings
            GROUP BY tier
            ORDER BY MIN(avg_mastery_score) DESC
        """).fetchall()
        
        return {
            "beings": {
                "total": being_stats["total_beings"],
                "generations": being_stats["max_generation"],
                "avg_mastery": round(being_stats["avg_mastery"] or 0, 4),
                "best_score_ever": being_stats["best_ever_score"],
                "total_rounds_played": being_stats["total_rounds_played"]
            },
            "tournaments": {
                "total": tournament_stats["total_tournaments"],
                "active": tournament_stats["active_tournaments"],
                "total_rounds": tournament_stats["tournament_rounds"]
            },
            "rounds": {
                "total": round_stats["total_rounds"],
                "avg_score": round(round_stats["avg_round_score"] or 0, 4),
                "max_score": round_stats["max_round_score"]
            },
            "top_performer": {
                "name": top_being["name"],
                "avg_mastery": top_being["avg_mastery_score"],
                "wins": top_being["wins"],
                "total_rounds": top_being["total_rounds"]
            } if top_being else None,
            "score_distribution": [dict(r) for r in score_distribution],
            "timestamp": datetime.now().isoformat()
        }


# --- Judge Endpoints ---

@app.get("/judges")
async def judge_performance():
    """Judge performance metrics."""
    with get_db() as conn:
        # Latest metrics per judge
        judges = conn.execute("""
            SELECT j1.*
            FROM judge_accuracy j1
            INNER JOIN (
                SELECT judge_name, MAX(evaluation_date) as max_date
                FROM judge_accuracy
                GROUP BY judge_name
            ) j2 ON j1.judge_name = j2.judge_name AND j1.evaluation_date = j2.max_date
            ORDER BY j1.f1_score DESC
        """).fetchall()
        
        results = []
        for j in judges:
            jd = row_to_dict(j)
            results.append({
                "judge_name": jd["judge_name"],
                "evaluation_date": jd["evaluation_date"],
                "precision": round(jd["precision"] or 0, 4),
                "recall": round(jd["recall"] or 0, 4),
                "f1_score": round(jd["f1_score"] or 0, 4),
                "accuracy": round(jd["accuracy"] or 0, 4),
                "correlation": round(jd["score_vs_conversion_correlation"] or 0, 4),
                "total_correlations": jd["total_correlations"],
                "detailed_metrics": jd.get("detailed_metrics_json")
            })
        
        # Calculate aggregate
        if results:
            avg_f1 = sum(j["f1_score"] for j in results) / len(results)
            avg_accuracy = sum(j["accuracy"] for j in results) / len(results)
        else:
            avg_f1 = avg_accuracy = 0
        
        return {
            "judges": results,
            "aggregate": {
                "judge_count": len(results),
                "avg_f1_score": round(avg_f1, 4),
                "avg_accuracy": round(avg_accuracy, 4)
            },
            "timestamp": datetime.now().isoformat()
        }


# --- Round Endpoints ---

@app.get("/rounds/recent")
async def recent_rounds(
    limit: int = Query(20, ge=1, le=100),
    being_id: Optional[str] = None,
    tournament_id: Optional[str] = None
):
    """Get recent round results."""
    with get_db() as conn:
        query = """
            SELECT r.*, b.name as being_name
            FROM rounds r
            LEFT JOIN beings b ON r.being_id = b.id
            WHERE 1=1
        """
        params = []
        
        if being_id:
            query += " AND r.being_id = ?"
            params.append(being_id)
        
        if tournament_id:
            query += " AND r.tournament_id = ?"
            params.append(tournament_id)
        
        query += " ORDER BY r.created_at DESC LIMIT ?"
        params.append(limit)
        
        rounds = conn.execute(query, params).fetchall()
        
        results = []
        for r in rounds:
            rd = row_to_dict(r)
            # Truncate response for list view
            if rd.get("response") and len(rd["response"]) > 200:
                rd["response_preview"] = rd["response"][:200] + "..."
                del rd["response"]
            results.append(rd)
        
        return {"rounds": results, "count": len(results)}


# --- Tournament Endpoints ---

@app.post("/tournament/start")
async def start_tournament(request: TournamentStartRequest):
    """Start a new tournament."""
    tournament_id = f"tournament_{uuid.uuid4().hex[:8]}"
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tournaments (id, mode, status, beings_count, config_json, started_at)
            VALUES (?, ?, 'pending', ?, ?, ?)
        """, [
            tournament_id,
            request.mode,
            request.beings_count or 0,
            json.dumps(request.config) if request.config else None,
            datetime.now().isoformat()
        ])
        conn.commit()
        
        return {
            "tournament_id": tournament_id,
            "mode": request.mode,
            "status": "pending",
            "message": "Tournament created. Use colosseum CLI to run it.",
            "started_at": datetime.now().isoformat()
        }


@app.get("/tournaments")
async def list_tournaments(limit: int = Query(10, ge=1, le=50)):
    """List tournaments."""
    with get_db() as conn:
        tournaments = conn.execute("""
            SELECT * FROM tournaments
            ORDER BY started_at DESC
            LIMIT ?
        """, [limit]).fetchall()
        
        return {"tournaments": [row_to_dict(t) for t in tournaments]}


@app.get("/tournaments/{tournament_id}")
async def get_tournament(tournament_id: str):
    """Get tournament details."""
    with get_db() as conn:
        tournament = conn.execute(
            "SELECT * FROM tournaments WHERE id = ?",
            [tournament_id]
        ).fetchone()
        
        if not tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")
        
        td = row_to_dict(tournament)
        
        # Get rounds for this tournament
        rounds = conn.execute("""
            SELECT r.being_id, b.name as being_name, 
                   COUNT(*) as rounds, SUM(CASE WHEN r.won THEN 1 ELSE 0 END) as wins,
                   AVG(r.mastery_score) as avg_score
            FROM rounds r
            LEFT JOIN beings b ON r.being_id = b.id
            WHERE r.tournament_id = ?
            GROUP BY r.being_id
            ORDER BY avg_score DESC
        """, [tournament_id]).fetchall()
        
        td["participants"] = [dict(r) for r in rounds]
        
        return td


# --- Main ---

if __name__ == "__main__":
    print(f"🏛️  Colosseum API starting on port {PORT}")
    print(f"📊 Database: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
