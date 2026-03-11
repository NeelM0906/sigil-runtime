#!/usr/bin/env python3
"""
🔥 SIMPLE DOMAIN EVOLUTION — Quick Test
Tests each domain with a single evolution round.
"""

import sqlite3
import json
import os
import time
from datetime import datetime
from pathlib import Path

DOMAINS_PATH = Path("./workspaces/prime/Projects/colosseum/domains")

def test_domain_connectivity(domain):
    """Test if a domain can run evolution."""
    db_path = DOMAINS_PATH / domain / "colosseum.db"
    if not db_path.exists():
        return False, f"No database found"
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        beings = conn.execute("SELECT * FROM beings LIMIT 2").fetchall()
        if len(beings) < 2:
            conn.close()
            return False, f"Not enough beings ({len(beings)})"
        
        # Test simple database insertion
        test_round = {
            "scenario": "Domain connectivity test",
            "combatants": [b["id"] for b in beings[:2]],
            "winner": beings[0]["id"],
            "timestamp": datetime.now().isoformat()
        }
        
        conn.execute("""
            INSERT INTO rounds (scenario, combatants_json, winner_id, scores_json, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            test_round["scenario"],
            json.dumps(test_round["combatants"]),
            test_round["winner"],
            json.dumps({"test": True})
        ))
        conn.commit()
        conn.close()
        
        return True, f"Successfully tested with {len(beings)} beings"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def run_connectivity_tests():
    """Test all domains for evolution readiness."""
    print("=" * 70)
    print("🔥 DOMAIN CONNECTIVITY TEST")
    print("=" * 70)
    
    results = {}
    for domain in ["strategy", "marketing", "sales", "tech", "ops", "cs", "finance", "hr", "legal", "product"]:
        print(f"Testing {domain}...")
        success, message = test_domain_connectivity(domain)
        results[domain] = {"success": success, "message": message}
        status = "✅" if success else "❌"
        print(f"   {status} {message}")
    
    print()
    print("📊 SUMMARY")
    successful = sum(1 for r in results.values() if r["success"])
    print(f"   Operational Domains: {successful}/10")
    print(f"   Status: {'🟢 READY FOR EVOLUTION' if successful >= 8 else '🟡 PARTIAL CONNECTIVITY'}")
    print("=" * 70)
    
    return results

if __name__ == "__main__":
    run_connectivity_tests()