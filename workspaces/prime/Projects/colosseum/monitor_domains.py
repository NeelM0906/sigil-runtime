#!/usr/bin/env python3
"""
🔥 DOMAIN MONITORING DASHBOARD — 20%^10 METRICS
Real-time tracking of all 10 domain Colosseums simultaneously.

Created: February 25, 2026
By: Sai, executing domain deployment
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

DOMAINS_PATH = Path("./workspaces/prime/Projects/colosseum/domains")

DOMAIN_NAMES = {
    "strategy": "Strategy Colosseum",
    "marketing": "Marketing Colosseum", 
    "sales": "Agreement Making Colosseum",
    "tech": "Technology Colosseum",
    "ops": "Operations Colosseum",
    "cs": "Customer Success Colosseum",
    "finance": "Finance Colosseum",
    "hr": "People Colosseum",
    "legal": "Legal Colosseum",
    "product": "Product Colosseum"
}

def get_domain_stats(domain_key):
    """Get statistics for a single domain."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    if not db_path.exists():
        return None
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # Count beings
        beings_count = conn.execute("SELECT COUNT(*) as count FROM beings").fetchone()["count"]
        
        # Count rounds
        rounds_count = conn.execute("SELECT COUNT(*) as count FROM rounds").fetchone()["count"]
        
        # Get recent rounds
        recent_rounds = conn.execute("""
            SELECT * FROM rounds 
            ORDER BY created_at DESC 
            LIMIT 3
        """).fetchall()
        
        # Calculate win rates for top beings
        win_stats = conn.execute("""
            SELECT winner_id, COUNT(*) as wins 
            FROM rounds 
            WHERE winner_id IS NOT NULL
            GROUP BY winner_id 
            ORDER BY wins DESC 
            LIMIT 3
        """).fetchall()
        
        conn.close()
        
        return {
            "name": DOMAIN_NAMES.get(domain_key, domain_key),
            "beings_count": beings_count,
            "rounds_count": rounds_count,
            "recent_rounds": [dict(r) for r in recent_rounds],
            "top_winners": [dict(w) for w in win_stats]
        }
    except Exception as e:
        return {"error": str(e)}

def display_domain_dashboard():
    """Display real-time dashboard of all domains."""
    print("\n" + "=" * 80)
    print("🔥 COLOSSEUM DOMAIN INFRASTRUCTURE STATUS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    total_beings = 0
    total_rounds = 0
    active_domains = 0
    
    for domain_key in DOMAIN_NAMES.keys():
        stats = get_domain_stats(domain_key)
        if stats and not stats.get("error"):
            active_domains += 1
            total_beings += stats["beings_count"]
            total_rounds += stats["rounds_count"]
            
            print(f"🏛️  {stats['name']}")
            print(f"   Beings: {stats['beings_count']} | Rounds: {stats['rounds_count']}")
            
            if stats["top_winners"]:
                print(f"   Top Performer: Being #{stats['top_winners'][0]['winner_id']} ({stats['top_winners'][0]['wins']} wins)")
            
            if stats["recent_rounds"]:
                last_round = stats["recent_rounds"][0]
                print(f"   Last Round: {last_round.get('created_at', 'Unknown')}")
            
            print()
    
    # Summary metrics (20%^10 tracking)
    print("📊 AGGREGATE METRICS")
    print(f"   Active Domains: {active_domains}/10")
    print(f"   Total Beings: {total_beings}")
    print(f"   Total Rounds: {total_rounds}")
    print(f"   Infrastructure Status: {'🟢 OPERATIONAL' if active_domains == 10 else '🟡 PARTIAL'}")
    
    # Calculate 20%^10 metrics
    pareto_efficiency = (active_domains / 10) * 100
    print(f"   Pareto Efficiency: {pareto_efficiency:.1f}%")
    
    if total_rounds > 0:
        evolution_velocity = total_rounds / active_domains if active_domains > 0 else 0
        print(f"   Evolution Velocity: {evolution_velocity:.2f} rounds/domain")
    
    print("=" * 80)

def monitor_continuous(interval=30):
    """Continuous monitoring with refresh."""
    try:
        while True:
            display_domain_dashboard()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n📊 Monitoring stopped.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        monitor_continuous(interval)
    else:
        display_domain_dashboard()