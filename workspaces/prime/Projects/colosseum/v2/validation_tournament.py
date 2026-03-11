#!/usr/bin/env python3
"""
Miner 24 Validation Tournament
10 beings × 3 rounds × 17 judges (from judges_19.json) × 85 scenarios
Quick validation run to check system health
"""
import json, os, time, asyncio, random
from openai import AsyncOpenAI

client = AsyncOpenAI()

# Load data
print("🔍 Loading data files...")
DATA_DIR = "./workspaces/prime/Projects/colosseum/v2/data"

with open(f"{DATA_DIR}/beings.json") as f:
    ALL_BEINGS = json.load(f)
with open(f"{DATA_DIR}/judges_19.json") as f:
    JUDGES = json.load(f)
with open(f"{DATA_DIR}/scenarios_expanded.json") as f:
    SCENARIOS_RAW = json.load(f)

# Extract scenarios (skip _meta key)
SCENARIOS = {k: v for k, v in SCENARIOS_RAW.items() if not k.startswith("_")}

# Select 10 beings (mix of areas)
random.seed(42)  # Reproducible selection
BEINGS = random.sample(ALL_BEINGS, 10)

print(f"✅ Loaded: {len(ALL_BEINGS)} total beings (using 10), {len(JUDGES)} judges, {len(SCENARIOS)} scenarios")
print(f"\n📋 Selected beings for validation:")
for i, b in enumerate(BEINGS):
    print(f"   {i+1}. {b['title'][:40]:40s} | {b['area'][:25]}")

# Findings/issues list
ISSUES = []

# Group scenarios by difficulty
SCENARIOS_BY_DIFFICULTY = {"bronze": [], "silver": [], "gold": [], "platinum": []}
for sid, scenario in SCENARIOS.items():
    diff = scenario.get("difficulty", "bronze")
    if diff in SCENARIOS_BY_DIFFICULTY:
        SCENARIOS_BY_DIFFICULTY[diff].append(sid)

def select_scenario_for_round(used_scenarios, round_num):
    """Select an appropriate scenario based on round."""
    if round_num == 1:
        preferred_difficulty = "bronze"
    elif round_num == 2:
        preferred_difficulty = "silver"
    else:
        preferred_difficulty = "gold"
    
    candidates = [s for s in SCENARIOS_BY_DIFFICULTY.get(preferred_difficulty, []) if s not in used_scenarios]
    
    if not candidates:
        candidates = [s for s in SCENARIOS.keys() if s not in used_scenarios]
    
    if not candidates:
        candidates = list(SCENARIOS.keys())
    
    selected = random.choice(candidates)
    used_scenarios.add(selected)
    return SCENARIOS[selected], selected

async def generate_response(being, scenario, semaphore):
    """Have a being respond to its scenario."""
    async with semaphore:
        prompt = f"""SCENARIO: {scenario['title']}
COMPANY: {scenario['company']}
DIFFICULTY: {scenario['difficulty'].upper()}
SITUATION: {scenario['situation']}
PERSON: {json.dumps(scenario.get('person', {}))}
SUCCESS CRITERIA: {scenario['success_criteria']}

Respond as your character would in this exact situation. Be specific, be masterful, be real."""

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": being["dna"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.8
            )
            return resp.choices[0].message.content
        except Exception as e:
            ISSUES.append(f"Generation error for {being['title']}: {e}")
            return f"[ERROR: {e}]"

async def judge_response(judge_key, judge_data, being, scenario, response, semaphore):
    """Have a judge score a being's response."""
    async with semaphore:
        prompt = f"""BEING: {being['title']} ({being['area']})
SCENARIO: {scenario['title']} — {scenario['situation']}
DIFFICULTY: {scenario['difficulty'].upper()}
SUCCESS CRITERIA: {scenario['success_criteria']}

THE BEING'S RESPONSE:
{response}

Score this response according to your criteria. Be rigorous. Return ONLY valid JSON."""

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": judge_data["prompt"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            content = resp.choices[0].message.content
            # Try to extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            ISSUES.append(f"JSON parse error from {judge_key}: {str(e)[:50]}")
            return {"error": "JSON parse error", "overall": 5.0, "feedback": "Could not parse"}
        except Exception as e:
            ISSUES.append(f"Judge error ({judge_key}): {e}")
            return {"error": str(e), "overall": 5.0, "feedback": "Judge error"}

async def run_being_round(being, scenario, round_num, semaphore):
    """Run one being through one scenario with all judges."""
    response = await generate_response(being, scenario, semaphore)
    
    if response.startswith("[ERROR"):
        return None
    
    # Score with all judges in parallel
    judge_tasks = []
    for jkey, jdata in JUDGES.items():
        judge_tasks.append(judge_response(jkey, jdata, being, scenario, response, semaphore))
    
    scores = await asyncio.gather(*judge_tasks)
    judge_keys = list(JUDGES.keys())
    
    result = {
        "being_id": being["id"],
        "being_title": being["title"],
        "area": being["area"],
        "scenario_id": scenario.get("title", "unknown"),
        "scenario_company": scenario.get("company", "unknown"),
        "scenario_difficulty": scenario.get("difficulty", "unknown"),
        "round": round_num,
        "response": response,
        "scores": {},
        "timestamp": time.time()
    }
    
    overall_scores = []
    for i, jkey in enumerate(judge_keys):
        result["scores"][jkey] = scores[i]
        if isinstance(scores[i], dict) and "overall" in scores[i]:
            try:
                overall_scores.append(float(scores[i]["overall"]))
            except (ValueError, TypeError):
                pass
    
    result["average_overall"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    return result

async def run_tournament(rounds=3):
    """Run validation tournament — 10 beings, 3 rounds, 17 judges."""
    print(f"\n🏛️ VALIDATION TOURNAMENT — MINER 24")
    print(f"   {len(BEINGS)} beings × {rounds} rounds × {len(JUDGES)} judges")
    print(f"   {len(SCENARIOS)} available scenarios")
    print(f"   Estimated API calls: {len(BEINGS) * rounds * (len(JUDGES) + 1)}")
    print(f"{'='*70}\n")
    
    all_results = []
    start = time.time()
    
    # Semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(10)
    
    used_scenarios = set()
    
    for round_num in range(1, rounds + 1):
        print(f"\n🔔 ROUND {round_num}/{rounds}", end=" — ")
        if round_num == 1:
            print("🥉 BRONZE")
        elif round_num == 2:
            print("🥈 SILVER")
        else:
            print("🥇 GOLD")
        
        round_start = time.time()
        
        # Run all beings with their scenarios
        tasks = []
        for being in BEINGS:
            scenario, scenario_id = select_scenario_for_round(used_scenarios, round_num)
            tasks.append(run_being_round(being, scenario, round_num, semaphore))
        
        round_results = await asyncio.gather(*tasks)
        round_results = [r for r in round_results if r is not None]
        all_results.extend(round_results)
        
        round_time = time.time() - round_start
        print(f"   ⏱️ Round {round_num} complete: {len(round_results)} beings scored in {round_time:.1f}s")
        
        # Top 3 of the round
        sorted_results = sorted(round_results, key=lambda x: x["average_overall"], reverse=True)
        print(f"\n   🏆 TOP 3 THIS ROUND:")
        for j, r in enumerate(sorted_results[:3]):
            print(f"      {j+1}. {r['being_title'][:35]:35s} | {r['scenario_difficulty']:8s} | {r['average_overall']:.2f}")
        
        if round_num < rounds:
            await asyncio.sleep(1)
    
    total_time = time.time() - start
    
    # Calculate final leaderboard
    being_averages = {}
    for r in all_results:
        bid = r["being_id"]
        if bid not in being_averages:
            being_averages[bid] = {"title": r["being_title"], "area": r["area"], "scores": []}
        being_averages[bid]["scores"].append(r["average_overall"])
    
    leaderboard = []
    for bid, data in being_averages.items():
        avg = sum(data["scores"]) / len(data["scores"])
        leaderboard.append({
            "id": bid, 
            "title": data["title"], 
            "area": data["area"], 
            "average": avg,
            "total_rounds": len(data["scores"])
        })
    
    leaderboard.sort(key=lambda x: x["average"], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"🏛️ FINAL LEADERBOARD")
    print(f"   Total time: {total_time:.1f}s | Evaluations: {len(all_results) * len(JUDGES)}")
    print(f"{'='*70}\n")
    
    for i, entry in enumerate(leaderboard):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        print(f"{medal} {i+1:2d}. {entry['title']:40s} | {entry['average']:.2f}")
    
    # Save results
    timestamp = int(time.time())
    results_file = f"{DATA_DIR}/results/validation_{timestamp}.json"
    os.makedirs(f"{DATA_DIR}/results", exist_ok=True)
    with open(results_file, "w") as f:
        json.dump({
            "tournament_type": "validation",
            "leaderboard": leaderboard,
            "rounds": rounds,
            "beings_count": len(BEINGS),
            "judges_count": len(JUDGES),
            "scenarios_count": len(SCENARIOS),
            "total_time": total_time,
            "issues": ISSUES,
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to {results_file}")
    
    return leaderboard, ISSUES

if __name__ == "__main__":
    leaderboard, issues = asyncio.run(run_tournament(rounds=3))
    
    print(f"\n{'='*70}")
    print(f"📋 ISSUES DETECTED: {len(issues)}")
    if issues:
        for issue in issues[:10]:
            print(f"   ⚠️ {issue}")
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")
    print(f"{'='*70}")
