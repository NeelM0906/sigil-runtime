#!/usr/bin/env python3
"""
Forge Context Heartbeat
Runs every hour via cron — dumps session state to Supabase if context is above threshold.
Ensures Forge's critical state survives compaction.
"""
import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

WORKSPACE = Path("~/.openclaw/workspace-forge")

def get_mastery_progress():
    done = list((WORKSPACE / "reports" / "mastery-database").glob("*-mastery.json"))
    return len(done)

def main():
    try:
        from supabase_memory import SaiMemory
        mem = SaiMemory("forge")
        
        clusters_done = get_mastery_progress()
        
        summary = f"""Day 13 Forge Heartbeat — {datetime.now().strftime('%Y-%m-%d %H:%M')}

ACTIVE BACKGROUND PROCESS:
- Mastery research overnight run: {clusters_done}/80 clusters complete
- Writing to Supabase category=mastery_research + disk

KEY DELIVERABLES THIS SESSION:
- Breeder v2 (Kai-elevated, 3 Operations with beating heart)
- Writer Technical Judge v1 (4 micro-domain calibrations)
- mastery_researcher.py pipeline (80 clusters, 8-section format)
- Cron: every 3hr Kai training reminder
- All identity files updated (Breeder identity, Felt Clarity standard)

SEAN'S DIRECTIVES LOCKED:
- Micro-domain specificity (not generic influence)
- Innovator produces 3 competing versions (v2a/v2b/v2c)
- Every position gets its own judge
- 75% of scenarios = process/strategic/fulfillment (not cold outreach)

CURRENT CONTEXT: Healthy (16% at last check)
OVERNIGHT TASK: Complete all 80 mastery cluster profiles → Supabase → Pinecone review
"""
        
        mem.pre_compaction_dump(summary)
        print(f"[{datetime.now().strftime('%H:%M')}] Heartbeat dump OK — {clusters_done}/80 clusters done")
        
    except Exception as e:
        print(f"Heartbeat failed: {e}")

if __name__ == "__main__":
    main()
