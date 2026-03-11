"""
CHDDIA² Colosseum v2 — 108-Scenario Tournament
43 beings × 9 judges × 10 rounds × 108 expanded scenarios
"""
import json, os, time, asyncio, random
from openai import AsyncOpenAI

client = AsyncOpenAI()

# Load data
print("Loading data...")
with open("./workspaces/prime/Projects/colosseum/v2/data/beings.json") as f:
    BEINGS = json.load(f)
with open("./workspaces/prime/Projects/colosseum/v2/data/judges.json") as f:
    JUDGES = json.load(f)
with open("./workspaces/prime/Projects/colosseum/v2/data/scenarios_expanded.json") as f:
    SCENARIOS_RAW = json.load(f)

# Extract scenarios (skip _meta key)
SCENARIOS = {k: v for k, v in SCENARIOS_RAW.items() if not k.startswith("_")}

# Add 2 more judges to reach 9
JUDGES["brevity_judge"] = {
    "name": "Brevity Judge",
    "focus": "Economy of language - maximum impact with minimum words",
    "prompt": """You are the Brevity Judge in the ACT-I Colosseum. You evaluate beings on their ability to create MAXIMUM IMPACT with MINIMUM WORDS.

BREVITY IS MASTERY:
The more you know, the fewer words you need. Sean Callagy's patterns show this: when stakes are highest, he gets MORE concise, not less. Every word must earn its place.

CONTAMINATION SIGNALS (score LOWER):
- Overexplanation and caveats
- "To be clear..." "What I mean is..." "In other words..."
- Bullet points when one sentence would do
- Three paragraphs when one would hit harder
- Ending with "Does that make sense?" or "Let me know if you need clarification"
- Academic thoroughness when conversational punch is needed

MASTERY SIGNALS (score HIGHER):
- Says it once, powerfully
- Every word chosen deliberately
- Silences that create impact
- Knowing when NOT to speak
- One-line responses that land harder than essays
- The Hemingway principle: active voice, concrete nouns, strong verbs

SCORING (0-9.9999):
- WORD_ECONOMY: Maximum impact per word ratio
- CONFIDENCE: Says it without hedging or over-explaining
- PUNCH: Does it hit? First sentence impact?
- SILENCE_MASTERY: Knowing when less is more
- OVERALL: Overall brevity mastery

Return JSON: {"word_economy": X, "confidence": X, "punch": X, "silence_mastery": X, "overall": X, "feedback": "specific feedback"}"""
}

JUDGES["company_expertise_judge"] = {
    "name": "Company Expertise Judge",
    "focus": "Deep knowledge of the specific company's domain, processes, and unique value",
    "prompt": """You are the Company Expertise Judge in the ACT-I Colosseum. You evaluate whether a being ACTUALLY knows its company's domain deeply.

THREE COMPANIES, THREE DISTINCT DOMAINS:

CALLAGY RECOVERY:
- IDR (Independent Dispute Resolution) process under No Surprises Act
- Medical billing codes, claim denials, EOBs, balance billing
- Carrier negotiation tactics, legal leverage points
- Provider relationships, revenue cycle management
- No-win-no-fee contingency model

UNBLINDED:
- The 39-component Formula (Self Mastery, Influence Mastery, Process Mastery)
- 7 Levers + 0.5 (Shared Experiences, Ecosystem Mergers, Speaking, Meetings, Sales, Disposable Income, Contribution, Fun & Magic)
- Immersions, Academy, coaching methodologies
- Zone Action vs 80% activity distinction
- The 4 Energies, 4-Step Communication Model, 12 Indispensable Elements

ACT-I:
- Genesis Forge, Agent Builder Factory, ACT-I beings architecture
- Super Actualized Intelligence concepts
- AI agent deployment, DNA creation, training methodologies
- Technical knowledge meets Unblinded philosophy

SCORING (0-9.9999):
- DOMAIN_DEPTH: Does the being know specific terminology, processes, and details of its company?
- TERMINOLOGY_ACCURACY: Are terms used correctly (not generically)?
- PROCESS_KNOWLEDGE: Does the being understand the actual workflow/methodology?
- UNIQUE_VALUE_ARTICULATION: Can it explain why THIS company, not competitors?
- OVERALL: Overall company expertise

Return JSON: {"domain_depth": X, "terminology_accuracy": X, "process_knowledge": X, "unique_value": X, "overall": X, "feedback": "specific feedback"}"""
}

print(f"Loaded: {len(BEINGS)} beings, {len(JUDGES)} judges, {len(SCENARIOS)} scenarios")

RESULTS_DIR = "./workspaces/prime/Projects/colosseum/v2/data/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Group scenarios by company and difficulty
def organize_scenarios():
    """Organize scenarios for smart assignment."""
    by_company = {"Callagy Recovery": [], "Unblinded": [], "ACT-I": []}
    by_difficulty = {"bronze": [], "silver": [], "gold": [], "platinum": []}
    
    for sid, scenario in SCENARIOS.items():
        company = scenario.get("company", "")
        difficulty = scenario.get("difficulty", "bronze")
        
        if "Callagy" in company:
            by_company["Callagy Recovery"].append(sid)
        elif "Unblinded" in company:
            by_company["Unblinded"].append(sid)
        elif "ACT-I" in company or "ACT_I" in company:
            by_company["ACT-I"].append(sid)
        
        if difficulty in by_difficulty:
            by_difficulty[difficulty].append(sid)
    
    return by_company, by_difficulty

SCENARIOS_BY_COMPANY, SCENARIOS_BY_DIFFICULTY = organize_scenarios()

def select_scenario_for_being(being, used_scenarios, round_num):
    """Select an appropriate scenario for a being based on round progression."""
    # Determine company affinity from being's area
    area = being.get("area", "").lower()
    
    # Map areas to companies
    if "recovery" in area or "idr" in area or "carrier" in area:
        preferred_companies = ["Callagy Recovery"]
    elif "coaching" in area or "mastery" in area or "immersion" in area:
        preferred_companies = ["Unblinded"]
    elif "ai" in area or "act-i" in area or "agent" in area or "genesis" in area:
        preferred_companies = ["ACT-I"]
    else:
        # General areas can handle any company
        preferred_companies = ["Callagy Recovery", "Unblinded", "ACT-I"]
    
    # Determine difficulty based on round (escalating)
    if round_num <= 2:
        preferred_difficulty = "bronze"
    elif round_num <= 4:
        preferred_difficulty = "silver"
    elif round_num <= 7:
        preferred_difficulty = "gold"
    else:
        preferred_difficulty = "platinum"
    
    # Find scenarios matching both company and difficulty
    candidates = []
    for company in preferred_companies:
        company_scenarios = SCENARIOS_BY_COMPANY.get(company, [])
        for sid in company_scenarios:
            if sid not in used_scenarios:
                scenario = SCENARIOS[sid]
                if scenario.get("difficulty") == preferred_difficulty:
                    candidates.append(sid)
    
    # Fallback: any unused scenario matching difficulty
    if not candidates:
        diff_scenarios = SCENARIOS_BY_DIFFICULTY.get(preferred_difficulty, [])
        candidates = [s for s in diff_scenarios if s not in used_scenarios]
    
    # Fallback: any unused scenario
    if not candidates:
        candidates = [s for s in SCENARIOS.keys() if s not in used_scenarios]
    
    # Final fallback: reuse scenarios
    if not candidates:
        candidates = list(SCENARIOS.keys())
    
    selected = random.choice(candidates)
    used_scenarios.add(selected)
    return SCENARIOS[selected]

async def generate_response(being, scenario, semaphore):
    """Have a being respond to its scenario with rate limiting."""
    async with semaphore:
        prompt = f"""SCENARIO: {scenario['title']}
COMPANY: {scenario['company']}
DIFFICULTY: {scenario['difficulty'].upper()}
SITUATION: {scenario['situation']}
PERSON: {json.dumps(scenario.get('person', {}))}
SUCCESS CRITERIA: {scenario['success_criteria']}

Respond as your character would in this exact situation. Be specific, be masterful, be real. This is not a test — this is the moment. Execute."""

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": being["dna"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.8
            )
            return resp.choices[0].message.content
        except Exception as e:
            await asyncio.sleep(1)  # Brief pause on error
            return f"[ERROR: {e}]"

async def judge_response(judge_key, judge_data, being, scenario, response, semaphore):
    """Have a judge score a being's response with rate limiting."""
    async with semaphore:
        prompt = f"""BEING: {being['title']} ({being['area']})
SCENARIO: {scenario['title']} — {scenario['situation']}
DIFFICULTY: {scenario['difficulty'].upper()}
SUCCESS CRITERIA: {scenario['success_criteria']}

THE BEING'S RESPONSE:
{response}

Score this response according to your criteria. Be rigorous. Be specific. Return ONLY valid JSON."""

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": judge_data["prompt"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            content = resp.choices[0].message.content
            # Try to extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {"error": "JSON parse error", "overall": 5.0, "feedback": "Could not parse judge response"}
        except Exception as e:
            await asyncio.sleep(0.5)
            return {"error": str(e), "overall": 5.0, "feedback": "Judge error"}

async def run_being_round(being, scenario, round_num, semaphore):
    """Run one being through one scenario with all 9 judges."""
    # Generate response
    response = await generate_response(being, scenario, semaphore)
    
    if response.startswith("[ERROR"):
        return None
    
    # Score with all 9 judges in parallel
    judge_tasks = []
    for jkey, jdata in JUDGES.items():
        judge_tasks.append(judge_response(jkey, jdata, being, scenario, response, semaphore))
    
    scores = await asyncio.gather(*judge_tasks)
    judge_keys = list(JUDGES.keys())
    
    # Compile results
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

async def run_tournament(rounds=10):
    """Run full tournament — 43 beings, 108 scenarios, 9 judges, 10 rounds."""
    print(f"\n🏛️ CHDDIA² COLOSSEUM v2 — 108 SCENARIO TOURNAMENT")
    print(f"   {len(BEINGS)} beings × {rounds} rounds × {len(JUDGES)} judges")
    print(f"   108 expanded scenarios (Callagy/Unblinded/ACT-I)")
    print(f"   Total evaluations: ~{len(BEINGS) * rounds * len(JUDGES)}")
    print(f"{'='*70}\n")
    
    all_results = []
    start = time.time()
    
    # Semaphore to limit concurrent API calls (avoid rate limits)
    semaphore = asyncio.Semaphore(15)
    
    # Track used scenarios to maximize variety
    used_scenarios = set()
    
    for round_num in range(1, rounds + 1):
        print(f"\n🔔 ROUND {round_num}/{rounds} — Difficulty: ", end="")
        if round_num <= 2:
            print("🥉 BRONZE")
        elif round_num <= 4:
            print("🥈 SILVER")
        elif round_num <= 7:
            print("🥇 GOLD")
        else:
            print("💎 PLATINUM")
        
        round_start = time.time()
        
        # Assign scenarios to each being
        being_scenarios = []
        for being in BEINGS:
            scenario = select_scenario_for_being(being, used_scenarios, round_num)
            being_scenarios.append((being, scenario))
        
        # Run all beings in parallel (semaphore controls concurrency)
        tasks = []
        for being, scenario in being_scenarios:
            tasks.append(run_being_round(being, scenario, round_num, semaphore))
        
        round_results = await asyncio.gather(*tasks)
        round_results = [r for r in round_results if r is not None]
        all_results.extend(round_results)
        
        # Print round summary
        round_time = time.time() - round_start
        print(f"   ⏱️ Round {round_num} complete: {len(round_results)} beings scored in {round_time:.1f}s")
        
        # Top 5 of the round
        sorted_results = sorted(round_results, key=lambda x: x["average_overall"], reverse=True)
        print(f"\n   🏆 TOP 5 THIS ROUND:")
        for j, r in enumerate(sorted_results[:5]):
            print(f"      {j+1}. {r['being_title'][:35]:35s} | {r['scenario_difficulty']:8s} | {r['average_overall']:.2f}")
        
        # Bottom 3
        if len(sorted_results) >= 3:
            print(f"\n   📉 BOTTOM 3:")
            for r in sorted_results[-3:]:
                print(f"      • {r['being_title'][:35]:35s} | {r['scenario_difficulty']:8s} | {r['average_overall']:.2f}")
        
        # Save intermediate results after each round
        intermediate_file = f"{RESULTS_DIR}/tournament_108_intermediate.json"
        with open(intermediate_file, "w") as f:
            json.dump({"round": round_num, "results": all_results}, f)
        print(f"   💾 Intermediate save: {len(all_results)} total results")
        
        # Brief pause between rounds
        if round_num < rounds:
            await asyncio.sleep(2)
    
    total_time = time.time() - start
    
    # Calculate final leaderboard
    being_averages = {}
    being_by_difficulty = {}
    
    for r in all_results:
        bid = r["being_id"]
        diff = r["scenario_difficulty"]
        
        if bid not in being_averages:
            being_averages[bid] = {
                "title": r["being_title"], 
                "area": r["area"], 
                "scores": [],
                "by_difficulty": {"bronze": [], "silver": [], "gold": [], "platinum": []}
            }
        being_averages[bid]["scores"].append(r["average_overall"])
        if diff in being_averages[bid]["by_difficulty"]:
            being_averages[bid]["by_difficulty"][diff].append(r["average_overall"])
    
    leaderboard = []
    for bid, data in being_averages.items():
        avg = sum(data["scores"]) / len(data["scores"])
        
        # Calculate per-difficulty averages
        diff_avgs = {}
        for diff, scores in data["by_difficulty"].items():
            if scores:
                diff_avgs[diff] = sum(scores) / len(scores)
            else:
                diff_avgs[diff] = 0
        
        leaderboard.append({
            "id": bid, 
            "title": data["title"], 
            "area": data["area"], 
            "average": avg,
            "total_rounds": len(data["scores"]),
            "by_difficulty": diff_avgs
        })
    
    leaderboard.sort(key=lambda x: x["average"], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"🏛️ FINAL LEADERBOARD — {len(BEINGS)} beings, {rounds} rounds, {len(JUDGES)} judges")
    print(f"   Total time: {total_time/60:.1f} minutes | Evaluations: {len(all_results) * len(JUDGES)}")
    print(f"{'='*70}")
    
    for i, entry in enumerate(leaderboard):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        print(f"{medal} {i+1:2d}. {entry['title']:40s} | {entry['area'][:25]:25s} | {entry['average']:.2f}")
    
    # Save results
    timestamp = int(time.time())
    results_file = f"{RESULTS_DIR}/tournament_108_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump({
            "tournament_type": "108_scenarios",
            "leaderboard": leaderboard,
            "rounds": rounds,
            "total_beings": len(BEINGS),
            "total_judges": len(JUDGES),
            "total_scenarios": len(SCENARIOS),
            "total_evaluations": len(all_results) * len(JUDGES),
            "total_time": total_time,
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Full results saved to {results_file}")
    
    # Save leaderboard summary
    with open(f"{RESULTS_DIR}/leaderboard_108_latest.json", "w") as f:
        json.dump(leaderboard, f, indent=2)
    
    print(f"💾 Leaderboard saved to {RESULTS_DIR}/leaderboard_108_latest.json")
    
    return leaderboard, all_results

if __name__ == "__main__":
    leaderboard, results = asyncio.run(run_tournament(rounds=10))
