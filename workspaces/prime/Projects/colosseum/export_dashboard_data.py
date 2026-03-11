#!/usr/bin/env python3
"""
Dashboard Data Export System for ACT-I Colosseum
Exports tournament data in JSON format ready for Sabeen's dashboard.

Created by Miner 17 - Feb 23, 2026
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Paths
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "colosseum.db"
V2_DATA_PATH = PROJECT_ROOT / "v2" / "data"
EXPORT_PATH = PROJECT_ROOT / "dashboard_export"


def ensure_export_dir():
    """Create export directory if it doesn't exist."""
    EXPORT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"✓ Export directory ready: {EXPORT_PATH}")


def export_beings_v1():
    """Export all beings from SQLite database (v1 system)."""
    if not DB_PATH.exists():
        print(f"⚠ Database not found: {DB_PATH}")
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT id, name, generation, lineage, 
               wins, losses, total_rounds,
               avg_mastery_score, best_score,
               energy_json, traits_json, strengths_json, weaknesses_json,
               parent_ids_json, created_at
        FROM beings
        ORDER BY avg_mastery_score DESC
    """)
    
    beings = []
    for row in c.fetchall():
        being = dict(row)
        # Parse JSON fields
        being['energy'] = json.loads(being.pop('energy_json', '{}'))
        being['traits'] = json.loads(being.pop('traits_json', '[]'))
        being['strengths'] = json.loads(being.pop('strengths_json', '[]'))
        being['weaknesses'] = json.loads(being.pop('weaknesses_json', '[]'))
        being['parent_ids'] = json.loads(being.pop('parent_ids_json', '[]'))
        being['win_rate'] = being['wins'] / being['total_rounds'] if being['total_rounds'] > 0 else 0
        being['source'] = 'v1_sqlite'
        beings.append(being)
    
    conn.close()
    print(f"✓ Exported {len(beings)} beings from v1 database")
    return beings


def export_beings_v2():
    """Export all beings from v2 JSON files."""
    beings = []
    
    # Standard v2 beings
    beings_file = V2_DATA_PATH / "beings.json"
    if beings_file.exists():
        with open(beings_file) as f:
            v2_beings = json.load(f)
            for b in v2_beings:
                b['source'] = 'v2_standard'
            beings.extend(v2_beings)
            print(f"✓ Loaded {len(v2_beings)} beings from beings.json")
    
    # Ecosystem beings
    ecosystem_file = V2_DATA_PATH / "beings_ecosystem.json"
    if ecosystem_file.exists():
        with open(ecosystem_file) as f:
            eco_beings = json.load(f)
            for b in eco_beings:
                b['source'] = 'v2_ecosystem'
            beings.extend(eco_beings)
            print(f"✓ Loaded {len(eco_beings)} beings from beings_ecosystem.json")
    
    return beings


def export_judges():
    """Export all judges with their scoring dimensions."""
    judges = {}
    
    # Standard v2 judges
    judges_file = V2_DATA_PATH / "judges.json"
    if judges_file.exists():
        with open(judges_file) as f:
            standard_judges = json.load(f)
            for jid, j in standard_judges.items():
                j['source'] = 'v2_standard'
                j['id'] = jid
            judges.update(standard_judges)
            print(f"✓ Loaded {len(standard_judges)} judges from judges.json")
    
    # Expanded 19-judge panel
    judges_19_file = V2_DATA_PATH / "judges_19.json"
    if judges_19_file.exists():
        with open(judges_19_file) as f:
            expanded_judges = json.load(f)
            for jid, j in expanded_judges.items():
                j['source'] = 'v2_expanded'
                j['id'] = jid
            judges.update(expanded_judges)
            print(f"✓ Loaded {len(expanded_judges)} judges from judges_19.json")
    
    # Meta judge
    meta_file = V2_DATA_PATH / "meta_judge.json"
    if meta_file.exists():
        with open(meta_file) as f:
            meta_judge = json.load(f)
            meta_judge['source'] = 'v2_meta'
            meta_judge['id'] = 'meta_judge'
            judges['meta_judge'] = meta_judge
            print(f"✓ Loaded meta judge")
    
    # Extract scoring dimensions from each judge
    judges_export = []
    for jid, j in judges.items():
        judge_data = {
            'id': jid,
            'name': j.get('name', jid),
            'focus': j.get('focus', ''),
            'source': j.get('source', 'unknown'),
            'scoring_dimensions': extract_scoring_dimensions(j.get('prompt', '')),
        }
        judges_export.append(judge_data)
    
    return judges_export


def extract_scoring_dimensions(prompt):
    """Extract scoring dimension names from a judge prompt."""
    dimensions = []
    lines = prompt.split('\n')
    in_scoring = False
    
    for line in lines:
        line = line.strip()
        if 'SCORING' in line.upper() and '0-9' in line:
            in_scoring = True
            continue
        if in_scoring:
            if line.startswith('- ') and ':' in line:
                dim_name = line[2:line.index(':')].strip()
                dimensions.append(dim_name)
            elif line.startswith('Return JSON'):
                break
    
    return dimensions


def export_tournaments():
    """Export tournament results and history from SQLite."""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT id, mode, status, total_rounds, beings_count,
               config_json, started_at, finished_at
        FROM tournaments
        ORDER BY started_at DESC
    """)
    
    tournaments = []
    for row in c.fetchall():
        t = dict(row)
        t['config'] = json.loads(t.pop('config_json', '{}'))
        t['source'] = 'v1_sqlite'
        tournaments.append(t)
    
    conn.close()
    print(f"✓ Exported {len(tournaments)} tournaments from v1 database")
    
    # Also load v2 tournament results
    results_dir = V2_DATA_PATH / "results"
    if results_dir.exists():
        for result_file in results_dir.glob("tournament_*.json"):
            try:
                with open(result_file) as f:
                    # Just get metadata, not full results (too large)
                    content = f.read()
                    data = json.loads(content)
                    if isinstance(data, dict):
                        summary = {
                            'id': result_file.stem,
                            'source': 'v2_results',
                            'file_size_kb': len(content) / 1024,
                            'has_leaderboard': 'leaderboard' in data,
                            'has_round_results': 'round_results' in data,
                        }
                        if 'leaderboard' in data:
                            summary['top_3'] = data['leaderboard'][:3] if isinstance(data['leaderboard'], list) else []
                        tournaments.append(summary)
            except Exception as e:
                print(f"⚠ Error loading {result_file}: {e}")
    
    return tournaments


def export_round_history():
    """Export evolution history from rounds table."""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get round results with scores
    c.execute("""
        SELECT r.id, r.scenario_id, r.being_id, r.mastery_score, r.won,
               r.tournament_id, r.created_at, b.name as being_name, b.generation
        FROM rounds r
        LEFT JOIN beings b ON r.being_id = b.id
        ORDER BY r.created_at DESC
        LIMIT 500
    """)
    
    rounds = [dict(row) for row in c.fetchall()]
    conn.close()
    
    print(f"✓ Exported {len(rounds)} round results from v1 database")
    return rounds


def compute_top_performers():
    """Compute top performers by various categories."""
    top_performers = {
        'by_mastery': [],
        'by_win_rate': [],
        'by_generation': defaultdict(list),
        'by_lineage': defaultdict(list),
        'by_area': defaultdict(list),
        'by_type': defaultdict(list),
    }
    
    # Load v1 beings
    v1_beings = export_beings_v1() if DB_PATH.exists() else []
    
    # Top by mastery (v1)
    v1_sorted = sorted(v1_beings, key=lambda x: x.get('avg_mastery_score', 0), reverse=True)
    top_performers['by_mastery'] = [
        {
            'id': b['id'],
            'name': b['name'],
            'mastery_score': b['avg_mastery_score'],
            'generation': b['generation'],
            'lineage': b['lineage'],
            'source': 'v1'
        }
        for b in v1_sorted[:20]
    ]
    
    # Top by win rate (minimum 3 rounds)
    v1_with_rounds = [b for b in v1_beings if b.get('total_rounds', 0) >= 3]
    v1_by_winrate = sorted(v1_with_rounds, key=lambda x: x.get('win_rate', 0), reverse=True)
    top_performers['by_win_rate'] = [
        {
            'id': b['id'],
            'name': b['name'],
            'win_rate': b['win_rate'],
            'wins': b['wins'],
            'losses': b['losses'],
            'total_rounds': b['total_rounds'],
            'source': 'v1'
        }
        for b in v1_by_winrate[:20]
    ]
    
    # By generation
    for b in v1_beings:
        gen = b.get('generation', 0)
        top_performers['by_generation'][f'gen_{gen}'].append({
            'id': b['id'],
            'name': b['name'],
            'mastery_score': b['avg_mastery_score'],
        })
    # Sort each generation
    for gen in top_performers['by_generation']:
        top_performers['by_generation'][gen] = sorted(
            top_performers['by_generation'][gen],
            key=lambda x: x['mastery_score'],
            reverse=True
        )[:10]
    
    # By lineage
    for b in v1_beings:
        lineage = b.get('lineage', 'unknown')
        top_performers['by_lineage'][lineage].append({
            'id': b['id'],
            'name': b['name'],
            'mastery_score': b['avg_mastery_score'],
        })
    for lineage in top_performers['by_lineage']:
        top_performers['by_lineage'][lineage] = sorted(
            top_performers['by_lineage'][lineage],
            key=lambda x: x['mastery_score'],
            reverse=True
        )[:10]
    
    # Load v2 leaderboard for area/type breakdown
    leaderboard_file = V2_DATA_PATH / "results" / "leaderboard_latest.json"
    if leaderboard_file.exists():
        with open(leaderboard_file) as f:
            v2_leaderboard = json.load(f)
            
        # By area
        for b in v2_leaderboard:
            area = b.get('area', 'Unknown')
            top_performers['by_area'][area].append({
                'id': b['id'],
                'title': b.get('title', ''),
                'average': b.get('average', 0),
            })
        
        # By type (extract from id)
        for b in v2_leaderboard:
            being_id = b.get('id', '')
            if '_leader' in being_id:
                being_type = 'leader'
            elif '_zone_action' in being_id:
                being_type = 'zone_action'
            elif '_client_facing' in being_id:
                being_type = 'client_facing'
            else:
                being_type = 'other'
            top_performers['by_type'][being_type].append({
                'id': b['id'],
                'title': b.get('title', ''),
                'average': b.get('average', 0),
                'area': b.get('area', ''),
            })
        
        # Sort by_type
        for t in top_performers['by_type']:
            top_performers['by_type'][t] = sorted(
                top_performers['by_type'][t],
                key=lambda x: x['average'],
                reverse=True
            )[:10]
    
    # Convert defaultdicts to regular dicts for JSON serialization
    top_performers['by_generation'] = dict(top_performers['by_generation'])
    top_performers['by_lineage'] = dict(top_performers['by_lineage'])
    top_performers['by_area'] = dict(top_performers['by_area'])
    top_performers['by_type'] = dict(top_performers['by_type'])
    
    return top_performers


def export_evolution_history():
    """Track evolution patterns and lineage trees."""
    if not DB_PATH.exists():
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT id, name, generation, parent_ids_json, avg_mastery_score, lineage
        FROM beings
        ORDER BY generation, avg_mastery_score DESC
    """)
    
    beings = []
    for row in c.fetchall():
        b = dict(row)
        b['parent_ids'] = json.loads(b.pop('parent_ids_json', '[]'))
        beings.append(b)
    
    conn.close()
    
    # Build lineage trees
    evolution = {
        'generation_stats': defaultdict(lambda: {'count': 0, 'avg_mastery': 0, 'best': None}),
        'lineage_trees': {},
        'total_beings': len(beings),
        'max_generation': max([b['generation'] for b in beings]) if beings else 0,
    }
    
    # Calculate generation stats
    for b in beings:
        gen = b['generation']
        stats = evolution['generation_stats'][gen]
        stats['count'] += 1
        stats['avg_mastery'] += b['avg_mastery_score']
        if stats['best'] is None or b['avg_mastery_score'] > stats['best']['score']:
            stats['best'] = {'id': b['id'], 'name': b['name'], 'score': b['avg_mastery_score']}
    
    for gen in evolution['generation_stats']:
        stats = evolution['generation_stats'][gen]
        if stats['count'] > 0:
            stats['avg_mastery'] /= stats['count']
    
    evolution['generation_stats'] = dict(evolution['generation_stats'])
    
    # Track parent-child relationships
    parent_children = defaultdict(list)
    for b in beings:
        for parent_id in b['parent_ids']:
            parent_children[parent_id].append({
                'id': b['id'],
                'name': b['name'],
                'generation': b['generation'],
                'mastery': b['avg_mastery_score']
            })
    
    evolution['lineage_trees'] = dict(parent_children)
    
    return evolution


def generate_dashboard_summary():
    """Generate a high-level summary for dashboard overview."""
    summary = {
        'export_timestamp': datetime.now().isoformat(),
        'data_sources': {
            'v1_sqlite': str(DB_PATH),
            'v2_json': str(V2_DATA_PATH),
        },
        'counts': {
            'v1_beings': 0,
            'v2_beings': 0,
            'judges': 0,
            'tournaments': 0,
        },
        'highlights': {},
    }
    
    # Count v1 beings
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM beings")
        summary['counts']['v1_beings'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tournaments")
        summary['counts']['tournaments'] = c.fetchone()[0]
        
        # Get best performer
        c.execute("""
            SELECT name, avg_mastery_score FROM beings 
            WHERE total_rounds >= 3 
            ORDER BY avg_mastery_score DESC LIMIT 1
        """)
        best = c.fetchone()
        if best:
            summary['highlights']['best_v1_being'] = {'name': best[0], 'score': best[1]}
        
        conn.close()
    
    # Count v2 beings
    beings_file = V2_DATA_PATH / "beings.json"
    if beings_file.exists():
        with open(beings_file) as f:
            summary['counts']['v2_beings'] = len(json.load(f))
    
    # Count judges
    judges_19 = V2_DATA_PATH / "judges_19.json"
    if judges_19.exists():
        with open(judges_19) as f:
            summary['counts']['judges'] = len(json.load(f))
    
    # V2 top performer
    leaderboard = V2_DATA_PATH / "results" / "leaderboard_latest.json"
    if leaderboard.exists():
        with open(leaderboard) as f:
            lb = json.load(f)
            if lb:
                summary['highlights']['best_v2_being'] = {
                    'title': lb[0].get('title', ''),
                    'area': lb[0].get('area', ''),
                    'average': lb[0].get('average', 0)
                }
    
    return summary


def run_export():
    """Run the complete dashboard export."""
    print("=" * 60)
    print("ACT-I COLOSSEUM - Dashboard Data Export")
    print("=" * 60)
    print()
    
    ensure_export_dir()
    print()
    
    # 1. Export all beings with mastery scores
    print("📊 Exporting beings...")
    v1_beings = export_beings_v1()
    v2_beings = export_beings_v2()
    all_beings = v1_beings + v2_beings
    
    beings_export = {
        'exported_at': datetime.now().isoformat(),
        'total_count': len(all_beings),
        'v1_count': len(v1_beings),
        'v2_count': len(v2_beings),
        'beings': all_beings
    }
    
    with open(EXPORT_PATH / "beings.json", 'w') as f:
        json.dump(beings_export, f, indent=2)
    print(f"   → Saved to beings.json ({len(all_beings)} total beings)")
    print()
    
    # 2. Export all judges with scoring dimensions
    print("⚖️ Exporting judges...")
    judges = export_judges()
    
    judges_export = {
        'exported_at': datetime.now().isoformat(),
        'total_count': len(judges),
        'judges': judges
    }
    
    with open(EXPORT_PATH / "judges.json", 'w') as f:
        json.dump(judges_export, f, indent=2)
    print(f"   → Saved to judges.json ({len(judges)} judges)")
    print()
    
    # 3. Export tournament results and evolution history
    print("🏆 Exporting tournaments...")
    tournaments = export_tournaments()
    rounds = export_round_history()
    evolution = export_evolution_history()
    
    tournament_export = {
        'exported_at': datetime.now().isoformat(),
        'tournaments': tournaments,
        'recent_rounds': rounds,
        'evolution_history': evolution
    }
    
    with open(EXPORT_PATH / "tournaments.json", 'w') as f:
        json.dump(tournament_export, f, indent=2)
    print(f"   → Saved to tournaments.json ({len(tournaments)} tournaments, {len(rounds)} rounds)")
    print()
    
    # 4. Export top performers by category
    print("🥇 Computing top performers...")
    top_performers = compute_top_performers()
    
    with open(EXPORT_PATH / "top_performers.json", 'w') as f:
        json.dump(top_performers, f, indent=2)
    print(f"   → Saved to top_performers.json")
    print()
    
    # 5. Generate summary
    print("📋 Generating dashboard summary...")
    summary = generate_dashboard_summary()
    
    with open(EXPORT_PATH / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   → Saved to summary.json")
    print()
    
    # Print summary
    print("=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"Location: {EXPORT_PATH}")
    print(f"Files created:")
    for f in sorted(EXPORT_PATH.glob("*.json")):
        size = f.stat().st_size / 1024
        print(f"  • {f.name} ({size:.1f} KB)")
    print()
    print(f"Totals:")
    print(f"  • {summary['counts']['v1_beings']} v1 beings")
    print(f"  • {summary['counts']['v2_beings']} v2 beings")
    print(f"  • {summary['counts']['judges']} judges")
    print(f"  • {summary['counts']['tournaments']} tournaments")
    print()
    
    if summary['highlights'].get('best_v1_being'):
        b = summary['highlights']['best_v1_being']
        print(f"🏆 Best v1 being: {b['name']} (score: {b['score']:.3f})")
    if summary['highlights'].get('best_v2_being'):
        b = summary['highlights']['best_v2_being']
        print(f"🏆 Best v2 being: {b['title']} - {b['area']} (avg: {b['average']:.3f})")
    
    return summary


if __name__ == "__main__":
    run_export()
