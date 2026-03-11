#!/usr/bin/env python3
"""
ACT-I Mastery Database — Overnight Run
Researches all 80 clusters, saves to disk + Supabase
Skips already-completed clusters
"""
import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WORKSPACE = Path("~/.openclaw/workspace-forge")
OUTPUT_DIR = WORKSPACE / "reports" / "mastery-database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from mastery_researcher import CLUSTERS, research_cluster, save_profile, to_sheet_row
from supabase_memory import SaiMemory

def already_done(cluster_name: str) -> bool:
    return (OUTPUT_DIR / f"{cluster_name.lower()}-mastery.json").exists()

def save_to_supabase(profile: dict):
    try:
        mem = SaiMemory("forge")
        content = (
            f"CLUSTER: {profile['cluster']}\n"
            f"DOMAIN: {profile['domain']}\n"
            f"FAMILY: {profile['family']}\n"
            f"POSITIONS: {profile['positions']}\n"
            f"LEVER: {profile['lever']}\n\n"
            f"{profile['mastery_profile']}"
        )
        mem.remember(
            category="mastery_research",
            content=content,
            source=f"mastery_researcher_v1:{profile['cluster']}",
            importance=8
        )
        return True
    except Exception as e:
        print(f"   Supabase error: {e}")
        return False

def main():
    pending = [(name, info) for name, info in CLUSTERS.items() if not already_done(name)]
    done_count = len(CLUSTERS) - len(pending)
    
    print(f"🔬 Overnight run: {len(pending)} remaining / {len(CLUSTERS)} total")
    print(f"✅ Already done: {done_count}")
    
    completed = 0
    errors = 0
    
    for cluster_name, cluster_info in pending:
        print(f"\n[{completed+1}/{len(pending)}] {cluster_name} — {cluster_info['domain']}")
        try:
            profile = research_cluster(cluster_name, cluster_info)
            save_profile(profile)
            supabase_ok = save_to_supabase(profile)
            status = "✅ disk+supabase" if supabase_ok else "✅ disk only"
            print(f"   {status} ({len(profile['mastery_profile'])} chars)")
            completed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            errors += 1
        
        time.sleep(3)  # rate limit courtesy
    
    print(f"\n{'='*50}")
    print(f"✅ Completed: {completed}")
    print(f"❌ Errors: {errors}")
    print(f"📂 Files: {OUTPUT_DIR}")
    
    # Log final status to Supabase
    try:
        mem = SaiMemory("forge")
        mem.remember(
            "mastery_research",
            f"OVERNIGHT RUN COMPLETE: {completed} clusters researched, {errors} errors. Total in database: {done_count + completed}/{len(CLUSTERS)} clusters.",
            "run_mastery_overnight.py",
            importance=9
        )
    except:
        pass

if __name__ == "__main__":
    main()
