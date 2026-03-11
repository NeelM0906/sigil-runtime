#!/usr/bin/env python3
"""
Email Colosseum API Server
Serves live battle data for the dashboard
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'email_ad.db')
PORT = 3347

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if self.path == '/api/leaderboard':
            self.handle_leaderboard()
        elif self.path == '/api/stats':
            self.handle_stats()
        elif self.path == '/api/personas':
            self.handle_personas()
        elif self.path == '/api/recent':
            self.handle_recent()
        elif self.path == '/health':
            self.wfile.write(json.dumps({'status': 'ok', 'db': DB_PATH}).encode())
        else:
            self.wfile.write(json.dumps({'error': 'Not found', 'endpoints': ['/api/leaderboard', '/api/stats', '/api/personas', '/api/recent', '/health']}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.end_headers()
    
    def handle_leaderboard(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, content, score, wins, losses, generation,
                   CASE WHEN (wins + losses) > 0 
                        THEN ROUND(wins * 100.0 / (wins + losses), 1) 
                        ELSE 0 END as win_rate
            FROM beings 
            ORDER BY score DESC 
            LIMIT 20
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.wfile.write(json.dumps(rows).encode())
    
    def handle_stats(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM battles")
        total_battles = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM beings")
        total_beings = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM personas")
        total_personas = cursor.fetchone()['total']
        cursor.execute("SELECT MAX(score) as top_score FROM beings")
        top_score = cursor.fetchone()['top_score']
        conn.close()
        self.wfile.write(json.dumps({
            'total_battles': total_battles,
            'total_beings': total_beings,
            'total_personas': total_personas,
            'top_score': top_score
        }).encode())
    
    def handle_personas(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, archetype, description FROM personas")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.wfile.write(json.dumps(rows).encode())
    
    def handle_recent(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.id, b.created_at,
                   a.content as being_a, bb.content as being_b,
                   w.content as winner,
                   p.name as judge,
                   b.scores_a, b.scores_b, b.reasoning
            FROM battles b
            JOIN beings a ON b.being_a_id = a.id
            JOIN beings bb ON b.being_b_id = bb.id
            JOIN beings w ON b.winner_id = w.id
            JOIN personas p ON b.persona_id = p.id
            ORDER BY b.created_at DESC
            LIMIT 10
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.wfile.write(json.dumps(rows).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress request logging

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), APIHandler)
    print(f"Email Colosseum API running on port {PORT}")
    print(f"Database: {DB_PATH}")
    print(f"Endpoints: /api/leaderboard, /api/stats, /api/personas, /api/recent, /health")
    server.serve_forever()
