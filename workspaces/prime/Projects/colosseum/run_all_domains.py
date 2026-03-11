#!/usr/bin/env python3
"""
🔥 PARALLEL DOMAIN EVOLUTION — 20%^10 EXECUTION
Runs ALL 10 domain Colosseums simultaneously.
Each domain evolves independently but in parallel.

Created: February 25, 2026 — Day 4
By: Sai, executing Sean's directive
"""

import sqlite3
import json
import os
import time
import threading
import random
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Initialize OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DOMAINS_PATH = Path("./workspaces/prime/Projects/colosseum/domains")

# Domain-specific scenarios
DOMAIN_SCENARIOS = {
    "strategy": [
        {"prompt": "A SaaS company is stuck at $2M ARR. Identify the Zone Action that will 10x their growth.", "tier": "gold"},
        {"prompt": "Two complementary businesses want to merge ecosystems. Design the integration strategy.", "tier": "platinum"},
        {"prompt": "A startup has 3 potential markets. Apply Pareto analysis to identify which to pursue.", "tier": "silver"},
    ],
    "marketing": [
        {"prompt": "Write a headline for a webinar that creates immediate emotional rapport with burned-out executives.", "tier": "gold"},
        {"prompt": "Design an email sequence that moves prospects through all 4 steps of the communication model.", "tier": "platinum"},
        {"prompt": "Create landing page copy that articulates the HUI for business owners seeking freedom.", "tier": "gold"},
    ],
    "sales": [
        {"prompt": "Prospect says 'I need to think about it.' Handle this using truth-to-pain.", "tier": "platinum"},
        {"prompt": "Conduct discovery call opening that establishes emotional rapport in 30 seconds.", "tier": "gold"},
        {"prompt": "Close a deal where the prospect loves the product but has genuine budget constraints.", "tier": "platinum"},
    ],
    "tech": [
        {"prompt": "Design API architecture that enables 10 ecosystem partners to integrate seamlessly.", "tier": "gold"},
        {"prompt": "Create monitoring system that tracks Pareto efficiency metrics across all services.", "tier": "silver"},
        {"prompt": "Build automation that eliminates 80% manual processes while maintaining quality.", "tier": "gold"},
    ],
    "ops": [
        {"prompt": "Client onboarding takes 30 days. Redesign to deliver value in 48 hours.", "tier": "platinum"},
        {"prompt": "Team is doing lots of activity but output is low. Identify and eliminate the waste.", "tier": "gold"},
        {"prompt": "Create quality assurance process that catches contamination before it reaches clients.", "tier": "silver"},
    ],
    "cs": [
        {"prompt": "Customer hasn't logged in for 60 days. Re-engage them using emotional rapport.", "tier": "gold"},
        {"prompt": "Conduct quarterly business review that identifies Zone Action opportunities for the client.", "tier": "platinum"},
        {"prompt": "Transform an angry complaint into a deeper relationship and potential case study.", "tier": "gold"},
    ],
    "finance": [
        {"prompt": "Company has $500K cash but burning $80K/month. Create Zone Action financial strategy.", "tier": "platinum"},
        {"prompt": "Design budget allocation using Pareto principles for a growing startup.", "tier": "gold"},
        {"prompt": "Analyze cash flow to identify the 0.8% investment that will transform the business.", "tier": "gold"},
    ],
    "hr": [
        {"prompt": "Interview candidate to assess GHIC alignment: Growth-driven, Heart-centered, Integrous, Committed to mastery.", "tier": "gold"},
        {"prompt": "Design compensation structure that rewards Zone Action behavior over busy work.", "tier": "silver"},
        {"prompt": "Create training program that eliminates contaminated thinking in new hires.", "tier": "gold"},
    ],
    "legal": [
        {"prompt": "Draft partnership agreement for ecosystem merger that protects both parties with integrity.", "tier": "gold"},
        {"prompt": "Negotiate contract terms with difficult counterparty using influence mastery.", "tier": "platinum"},
        {"prompt": "Assess compliance risk while maintaining speed and avoiding analysis paralysis.", "tier": "silver"},
    ],
    "product": [
        {"prompt": "Backlog has 200 features. Apply Zone Action framework to identify the 0.8% to build.", "tier": "platinum"},
        {"prompt": "Design user experience that creates emotional rapport within first 30 seconds.", "tier": "gold"},
        {"prompt": "Research user needs using Level 5 listening methodology.", "tier": "silver"},
    ],
}

def get_domain_judge_prompt(domain):
    """Create domain-specific judge prompt."""
    return f"""You are a judge for the {domain.upper()} domain Colosseum.

Score this response on these dimensions (0-10 each):
1. DOMAIN EXPERTISE — Technical accuracy and depth in {domain}
2. UNBLINDED ALIGNMENT — Filtered through Zone Action, 4-Step Model, Pareto thinking
3. ACTIONABILITY — Can this be executed immediately?
4. PARETO EFFICIENCY — Is this the 20%^10 move or 80% activity?
5. OVERALL MASTERY — Holistic score considering all factors

A score of 9+ is RARE and means exceptional mastery.
A score of 8+ is very good.
A score of 7+ is competent.
Below 7 needs improvement.

DO NOT use "no 10 exists" thinking. 10.0 is achievable for perfect responses.

Return JSON:
{{"domain_expertise": X, "unblinded_alignment": X, "actionability": X, "pareto_efficiency": X, "overall_mastery": X, "feedback": "..."}}
"""

def run_domain_round(domain):
    """Run one round of evolution in a domain."""
    db_path = DOMAINS_PATH / domain / "colosseum.db"
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Get beings
    beings = conn.execute("SELECT * FROM beings ORDER BY RANDOM() LIMIT 4").fetchall()
    if len(beings) < 2:
        conn.close()
        return None
    
    # Get scenario
    scenarios = DOMAIN_SCENARIOS.get(domain, [{"prompt": "Demonstrate mastery in your domain.", "tier": "gold"}])
    scenario = random.choice(scenarios)
    
    # Have each being respond
    responses = []
    for being in beings:
        try:
            response = client.chat.completions.create(
                model = "gpt-4o",
                messages=[
                    {"role": "system", "content": being["system_prompt"]},
                    {"role": "user", "content": scenario["prompt"]}
                ],
                temperature=0.7,
                max_tokens=500
            )
            responses.append({
                "being": being,
                "response": response.choices[0].message.content
            })
        except Exception as e:
            print(f"  Error generating response for {being['name']}: {e}")
    
    if len(responses) < 2:
        conn.close()
        return None
    
    # Judge responses
    scores = []
    for r in responses:
        try:
            judgment = client.chat.completions.create(
                model = "gpt-4o",
                messages=[
                    {"role": "system", "content": get_domain_judge_prompt(domain)},
                    {"role": "user", "content": f"SCENARIO: {scenario['prompt']}\n\nRESPONSE FROM {r['being']['name']}:\n{r['response']}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            score_data = json.loads(judgment.choices[0].message.content)
            scores.append({
                "being_id": r["being"]["id"],
                "name": r["being"]["name"],
                "score": score_data.get("overall_mastery", 5.0),
                "full_scores": score_data
            })
        except Exception as e:
            print(f"  Error judging {r['being']['name']}: {e}")
            scores.append({"being_id": r["being"]["id"], "name": r["being"]["name"], "score": 5.0})
    
    # Find winner
    winner = max(scores, key=lambda x: x["score"])
    
    # Update stats
    for s in scores:
        if s["being_id"] == winner["being_id"]:
            conn.execute("UPDATE beings SET wins = wins + 1, best_score = MAX(best_score, ?) WHERE id = ?",
                        (s["score"], s["being_id"]))
        else:
            conn.execute("UPDATE beings SET losses = losses + 1 WHERE id = ?", (s["being_id"],))
    
    # Log round
    conn.execute("""
        INSERT INTO rounds (scenario, combatants_json, winner_id, scores_json)
        VALUES (?, ?, ?, ?)
    """, (scenario["prompt"], json.dumps([s["name"] for s in scores]), winner["being_id"], json.dumps(scores)))
    
    conn.commit()
    conn.close()
    
    return {
        "domain": domain,
        "scenario": scenario["prompt"][:50] + "...",
        "winner": winner["name"],
        "score": winner["score"],
        "participants": len(scores)
    }

def domain_evolution_loop(domain, rounds=10, delay=5):
    """Evolution loop for a single domain."""
    print(f"🏛️  {domain.upper()} Colosseum starting...")
    
    for i in range(rounds):
        result = run_domain_round(domain)
        if result:
            print(f"   [{domain}] Round {i+1}: {result['winner']} wins with {result['score']:.2f}")
        time.sleep(delay)
    
    print(f"✅ {domain.upper()} Colosseum completed {rounds} rounds")

def run_all_parallel(rounds_per_domain=5, delay=3):
    """Run ALL domains in parallel threads."""
    print("=" * 70)
    print("🔥 PARALLEL DOMAIN EVOLUTION — 20%^10 EXECUTION")
    print("=" * 70)
    print(f"Starting {len(DOMAIN_SCENARIOS)} domains in PARALLEL")
    print(f"Rounds per domain: {rounds_per_domain}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    threads = []
    for domain in DOMAIN_SCENARIOS.keys():
        t = threading.Thread(target=domain_evolution_loop, args=(domain, rounds_per_domain, delay))
        threads.append(t)
        t.start()
    
    # Wait for all to complete
    for t in threads:
        t.join()
    
    print()
    print("=" * 70)
    print("🔥 ALL DOMAINS EVOLVED IN PARALLEL")
    print("=" * 70)

if __name__ == "__main__":
    import sys
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_all_parallel(rounds_per_domain=rounds, delay=2)
