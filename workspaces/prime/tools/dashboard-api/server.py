#!/usr/bin/env python3
"""
Live Dashboard API for Colosseum Stats
Serves real-time data for tournament brackets dashboard
"""

from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)

COLOSSEUM_PATH = Path("./workspaces/prime/Projects/colosseum")

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/stats')
def get_stats():
    """Get overall tournament stats"""
    main_db = COLOSSEUM_PATH / "colosseum.db"
    
    stats = {
        "main_beings": 0,
        "main_rounds": 0,
        "domain_beings": 0,
        "domain_rounds": 0,
        "domains": {}
    }
    
    # Main colosseum
    if main_db.exists():
        conn = get_db_connection(main_db)
        stats["main_beings"] = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
        try:
            stats["main_rounds"] = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
        except:
            stats["main_rounds"] = 0
        conn.close()
    
    # Domain colosseums
    domains = ["strategy", "marketing", "sales", "tech", "ops", "cs", "finance", "hr", "legal", "product"]
    for domain in domains:
        db_path = COLOSSEUM_PATH / "domains" / domain / "colosseum.db"
        if db_path.exists():
            conn = get_db_connection(db_path)
            beings = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
            try:
                rounds = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
            except:
                rounds = 0
            stats["domains"][domain] = {"beings": beings, "rounds": rounds}
            stats["domain_beings"] += beings
            stats["domain_rounds"] += rounds
            conn.close()
    
    stats["total_beings"] = stats["main_beings"] + stats["domain_beings"]
    stats["total_rounds"] = stats["main_rounds"] + stats["domain_rounds"]
    
    return jsonify(stats)

@app.route('/api/champions')
def get_champions():
    """Get all domain champions with real scores"""
    champions = {}
    
    # Main colosseum
    main_db = COLOSSEUM_PATH / "colosseum.db"
    if main_db.exists():
        conn = get_db_connection(main_db)
        row = conn.execute("""
            SELECT name, best_score, avg_mastery_score, generation, wins, losses 
            FROM beings ORDER BY best_score DESC LIMIT 1
        """).fetchone()
        if row:
            champions["influence"] = dict(row)
        conn.close()
    
    # Domain colosseums
    domains = ["strategy", "marketing", "sales", "tech", "ops", "cs", "finance", "hr", "legal", "product"]
    for domain in domains:
        db_path = COLOSSEUM_PATH / "domains" / domain / "colosseum.db"
        if db_path.exists():
            conn = get_db_connection(db_path)
            row = conn.execute("""
                SELECT name, best_score, avg_score, wins, losses 
                FROM beings ORDER BY best_score DESC LIMIT 1
            """).fetchone()
            if row:
                champions[domain] = dict(row)
            conn.close()
    
    return jsonify(champions)

@app.route('/api/top/<domain>')
def get_top_beings(domain):
    """Get top 10 beings for a domain"""
    if domain == "influence":
        db_path = COLOSSEUM_PATH / "colosseum.db"
    else:
        db_path = COLOSSEUM_PATH / "domains" / domain / "colosseum.db"
    
    if not db_path.exists():
        return jsonify({"error": "Domain not found"}), 404
    
    conn = get_db_connection(db_path)
    if domain == "influence":
        rows = conn.execute("""
            SELECT name, best_score, avg_mastery_score as avg_score, generation, wins, losses 
            FROM beings ORDER BY best_score DESC LIMIT 10
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT name, best_score, avg_score, wins, losses, generation
            FROM beings ORDER BY best_score DESC LIMIT 10
        """).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3350, debug=False)
