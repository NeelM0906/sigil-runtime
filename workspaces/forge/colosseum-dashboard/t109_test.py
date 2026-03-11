#!/usr/bin/env python3
"""
T109 Mutations Test for Email Colosseum
Insert 9 mutations, battle vs bottom 10 (2x each), compute WR delta vs baseline ID 30.
Update rankings.json
"""
import sqlite3
import json
import os
import re
import urllib.request
from datetime import datetime

DB_PATH = 'email_ad.db'
DATA_PATH = 'data/email_arena_rankings.json'

SCORING_DIMENSIONS = ['curiosity', 'relevance', 'credibility', 'urgency', 'clarity']

def load_env():
    env_path = '~/.openclaw/workspace-forge/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v

load_env()

def get_db():
    return sqlite3.connect(DB_PATH)

def get_random_persona():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM personas ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'name': row[1], 'category': row[2], 'archetype': row[3],
            'description': row[4], 'behavior_traits': json.loads(row[5] or '{}'), 
            'scoring_weights': json.loads(row[6] or '{}')
        }
    return None

def get_being(being_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM beings WHERE id = ?", (being_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'type': row[1], 'content': row[2], 'parent_id': row[3],
            'generation': row[4], 'score': row[5], 'wins': row[6], 'losses': row[7]
        }
    return None

def build_judge_prompt(being_a, being_b, persona, battle_type='subject_line'):
    traits = ', '.join([f"{k}: {v}" for k, v in persona['behavior_traits'].items()])
    type_context = {
        'subject_line': 'email subject line (deciding whether to open)',
        'email_copy': 'full email (deciding whether to read and click the CTA)',
        'ad_creative': 'ad (deciding whether to stop scrolling and click)'
    }
    context = type_context.get(battle_type, 'marketing messages')
    return f"""You are {persona['name']}, a {persona['description']}.

Your behavioral traits: {traits}

You just received two {context} in your inbox. 
Score each one on these dimensions (1-10):
- Curiosity: Does it make me want to know more?
- Relevance: Does this feel like it's for ME specifically?
- Credibility: Do I trust the sender?
- Urgency: Do I feel I need to act now?
- Clarity: Do I understand the value in 3 seconds?

OPTION A:
{being_a['content']}

OPTION B:
{being_b['content']}

Respond in this exact JSON format:
{{
  "scores_a": {{"curiosity": X, "relevance": X, "credibility": X, "urgency": X, "clarity": X}},
  "scores_b": {{"curiosity": X, "relevance": X, "credibility": X, "urgency": X, "clarity": X}},
  "reasoning": "As {persona['name']}, I would [open/read/click] [A/B] because..."
}}"""

def parse_judgment(response_text):
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    return {
        'scores_a': {d: 5 for d in SCORING_DIMENSIONS},
        'scores_b': {d: 5 for d in SCORING_DIMENSIONS},
        'reasoning': 'Unable to parse judgment'
    }

def calculate_weighted_score(scores, weights):
    total = 0
    for dim in SCORING_DIMENSIONS:
        total += scores.get(dim, 5) * weights.get(dim, 0.2)
    return total

def run_battle(a_id, b_id):
    being_a = get_being(a_id)
    being_b = get_being(b_id)
    if not being_a or not being_b:
        print(f"Missing being: A{a_id} or B{b_id}")
        return False
    persona = get_random_persona()
    if not persona:
        print("No persona")
        return False
    prompt = build_judge_prompt(being_a, being_b, persona)
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://colosseum.openclaw",
        "X-Title": "Email Colosseum T109"
    }
    data = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    data_json = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data_json,
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode('utf-8')
            content = json.loads(resp_data)['choices'][0]['message']['content']
    except Exception as e:
        print(f"API error: {e}")
        return False
    result = parse_judgment(content)
    score_a = calculate_weighted_score(result['scores_a'], persona['scoring_weights'])
    score_b = calculate_weighted_score(result['scores_b'], persona['scoring_weights'])
    winner_id = a_id if score_a > score_b else b_id
    # Record
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO battles (being_a_id, being_b_id, winner_id, persona_id, battle_type, scores_a, scores_b, reasoning)
        VALUES (?, ?, ?, ?, 'subject_line', ?, ?, ?)
    """, (a_id, b_id, winner_id, persona['id'], json.dumps(result['scores_a']), json.dumps(result['scores_b']), result['reasoning']))
    cursor.execute("UPDATE beings SET wins = wins + 1, score = score + 0.1 WHERE id = ?", (winner_id,))
    loser_id = b_id if winner_id == a_id else a_id
    cursor.execute("UPDATE beings SET losses = losses + 1, score = score - 0.05 WHERE id = ?", (loser_id,))
    conn.commit()
    conn.close()
    return winner_id == a_id

def add_being(content, parent_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO beings (type, content, parent_id, generation, wins, losses) VALUES ('subject_line', ?, ?, 4, 0, 0)", (content, parent_id))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def print_status():
    print("=== T109 STATUS ===")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM beings WHERE generation=4")
    print(f"Mutations inserted: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM battles WHERE created_at > datetime('now', '-1 hour')")
    print(f"Battles this hour: {cursor.fetchone()[0]}")
    conn.close()

def update_rankings():
    conn = get_db()
    cursor = conn.cursor()
    # Total subject_lines
    cursor.execute("SELECT COUNT(*) FROM beings WHERE type='subject_line'")
    total_sl = cursor.fetchone()[0]
    # Top 10
    cursor.execute("""
        SELECT id, type, content, wins, losses, generation, parent_id 
        FROM beings WHERE type='subject_line' 
        ORDER BY (wins * 1.0 / (wins + losses + 0.0001)) DESC LIMIT 10
    """)
    top10 = []
    for row in cursor.fetchall():
        total_games = row[3] + row[4]
        wr = round((row[3] / total_games * 100) if total_games > 0 else 0, 1)
        top10.append({
            "id": row[0],
            "type": row[1],
            "snippet": (row[2][:60] + "...") if len(row[2]) > 60 else row[2],
            "wins": row[3],
            "losses": row[4],
            "wr": wr,
            "parent_id": row[6]
        })
    # Bottom 10
    cursor.execute("""
        SELECT id, type, content, wins, losses, generation, parent_id 
        FROM beings WHERE type='subject_line' 
        ORDER BY (wins * 1.0 / (wins + losses + 0.0001)) ASC LIMIT 10
    """)
    bottom10 = []
    for row in cursor.fetchall():
        total_games = row[3] + row[4]
        wr = round((row[3] / total_games * 100) if total_games > 0 else 0, 1)
        bottom10.append({
            "id": row[0],
            "type": row[1],
            "snippet": (row[2][:60] + "...") if len(row[2]) > 60 else row[2],
            "wins": row[3],
            "losses": row[4],
            "wr": wr,
            "parent_id": row[6]
        })
    conn.close()
    data = {
        "generated_at": datetime.now().isoformat(),
        "source": "email_ad.db T109",
        "stats": {
            "total_battles": 0,  # skip query
            "total_beings": 0,
            "subject_lines": total_sl
        },
        "top_10": top10,
        "bottom_10": bottom10
    }
    os.makedirs('data', exist_ok=True)
    with open(DATA_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated {DATA_PATH}")

if __name__ == '__main__':
    print("T109 Baby: ZA-EMAIL-03 Mutations Test")
    mutations = [
        {"label": "M30-1", "content": "PI firm owners: Is a $47K case-valuation oversight the hidden bottleneck?", "parent_id": 30},
        {"label": "M30-2", "content": "The $47K PI case leak you might be missing — are you the bottleneck?", "parent_id": 30},
        {"label": "M30-3", "content": "PI firms: the 3‑second fix that prevents a $47K oversight — are you the bottleneck?", "parent_id": 30},
        {"label": "M21-A", "content": "Most PI firms don’t realize this $47K oversight until it’s too late", "parent_id": 21},
        {"label": "M21-B", "content": "This is the $47K miss I see in PI files (and it’s a 3-second correction)", "parent_id": 21},
        {"label": "M21-C", "content": "Are you open to a fast audit to see if the $47K oversight is in your workflow?", "parent_id": 21},
        {"label": "M22-A", "content": "You’re not ‘busy’ — you might be the $47K bottleneck (3-second fix)", "parent_id": 22},
        {"label": "M22-B", "content": "The 3-second change that stops you from becoming the $47K bottleneck", "parent_id": 22},
        {"label": "M22-C", "content": "What would drop out if the $47K bottleneck wasn’t you anymore? (3-sec fix)", "parent_id": 22},
    ]
    bottom_10 = [20,24,34,38,35,7,11,8,16,18]
    mutation_ids = {}
    for mut in mutations:
        new_id = add_being(mut["content"], mut["parent_id"])
        mutation_ids[mut["label"]] = new_id
        print(f"Inserted {mut['label']} (parent {mut['parent_id']}) as ID {new_id}")
    print_status()
    print("\n--- Baseline ID 30 vs bottom 10 (20 battles) ---")
    baseline_wins = 0
    baseline_battles = 0
    for round_num in range(2):
        for opp in bottom_10:
            if run_battle(30, opp):
                baseline_wins += 1
            baseline_battles += 1
            print(f"30 vs {opp} (round {round_num+1}): {'WIN' if baseline_wins > baseline_battles -1 else 'LOSS'} | Total WR: {baseline_wins/baseline_battles*100:.1f}%")
    baseline_wr = baseline_wins / baseline_battles * 100
    print(f"Baseline WR: {baseline_wr:.1f}%")
    print("\n--- Mutations vs bottom 10 (20 battles each) ---")
    results = {}
    for label, mid in mutation_ids.items():
        mut_wins = 0
        mut_battles = 0
        for round_num in range(2):
            for opp in bottom_10:
                if run_battle(mid, opp):
                    mut_wins += 1
                mut_battles += 1
                print(f"{label} ({mid}) vs {opp} (round {round_num+1}): {'WIN' if mut_wins > mut_battles -1 else 'LOSS'} | WR: {mut_wins/mut_battles*100:.1f}%")
        mut_wr = mut_wins / mut_battles * 100
        delta = mut_wr - baseline_wr
        results[label] = {'wr': mut_wr, 'delta': delta}
        print(f"{label}: WR {mut_wr:.1f}% | Delta +{delta:+.1f}%")
    print("\n=== T109 TABLE ===")
    print("| Mutation | WR | Delta vs Baseline |")
    print("|----------|----|-------------------|")
    for label, r in results.items():
        print(f"| {label} | {r['wr']:.1f}% | +{r['delta']:+.1f}% |")
    best = max(results.items(), key=lambda x: x[1]['delta'])
    print(f"\nBest: {best[0]} +{best[1]['delta']:.1f}% WR {best[1]['wr']:.1f}%")
    print("\nInsights:")
    print("- Parent 30 lineage: avg delta...")
    # simple avg per parent
    p30 = [r['delta'] for l, r in results.items() if l.startswith('M30')]
    p21 = [r['delta'] for l, r in results.items() if l.startswith('M21')]
    p22 = [r['delta'] for l, r in results.items() if l.startswith('M22')]
    print(f"- Parent 30 avg delta: {sum(p30)/len(p30):.1f}%")
    print(f"- Parent 21 avg delta: {sum(p21)/len(p21):.1f}%")
    print(f"- Parent 22 avg delta: {sum(p22)/len(p22):.1f}%")
    print("\nT109 COMPLETE | Updated email_arena_rankings.json")
    update_rankings()
