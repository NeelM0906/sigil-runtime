"""
CHDDIA² Colosseum v2 — Tournament Engine
39 beings × 5 judges × area-specific scenarios
"""
import asyncio
import json
import os
import time
from pathlib import Path

from openai import AsyncOpenAI

from bomba_sr.openclaw.script_support import load_portable_env

load_portable_env(Path(__file__))

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"
MODEL_ID = os.getenv("BOMBA_COLOSSEUM_MODEL_ID") or os.getenv("BOMBA_MODEL_ID") or "anthropic/claude-opus-4.6"

_openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
_openai_key = os.getenv("OPENAI_API_KEY", "").strip()
if _openrouter_key:
    client = AsyncOpenAI(
        api_key=_openrouter_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
else:
    client = AsyncOpenAI(api_key=_openai_key or None)

# Load data
with (DATA_DIR / "beings.json").open(encoding="utf-8") as f:
    BEINGS = json.load(f)
with (DATA_DIR / "judges.json").open(encoding="utf-8") as f:
    JUDGES = json.load(f)
with (DATA_DIR / "scenarios.json").open(encoding="utf-8") as f:
    SCENARIOS = json.load(f)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

async def generate_response(being, scenario):
    """Have a being respond to its scenario."""
    prompt = f"""SCENARIO: {scenario['title']}
COMPANY: {scenario['company']}
SITUATION: {scenario['situation']}
PERSON: {json.dumps(scenario['person'])}
SUCCESS CRITERIA: {scenario['success_criteria']}

Respond as your character would in this exact situation. Be specific, be masterful, be real. This is not a test — this is the moment. Execute."""

    try:
        resp = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": being["dna"]},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.8
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR: {e}]"

async def judge_response(judge_key, judge_data, being, scenario, response):
    """Have a judge score a being's response."""
    prompt = f"""BEING: {being['title']} ({being['area']})
SCENARIO: {scenario['title']} — {scenario['situation']}
SUCCESS CRITERIA: {scenario['success_criteria']}

THE BEING'S RESPONSE:
{response}

Score this response according to your criteria. Be rigorous. Be specific. Return ONLY valid JSON."""

    try:
        resp = await client.chat.completions.create(
            model=MODEL_ID,
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
    except Exception as e:
        return {"error": str(e), "overall": 5.0, "feedback": "Judge error"}

async def run_round(being, scenario, round_num):
    """Run one being through one scenario with all 5 judges."""
    # Generate response
    response = await generate_response(being, scenario)
    
    # Score with all 5 judges in parallel
    judge_tasks = []
    for jkey, jdata in JUDGES.items():
        judge_tasks.append(judge_response(jkey, jdata, being, scenario, response))
    
    scores = await asyncio.gather(*judge_tasks)
    judge_keys = list(JUDGES.keys())
    
    # Compile results
    result = {
        "being_id": being["id"],
        "being_title": being["title"],
        "area": being["area"],
        "scenario": scenario["title"],
        "round": round_num,
        "response": response,
        "scores": {},
        "timestamp": time.time()
    }
    
    overall_scores = []
    for i, jkey in enumerate(judge_keys):
        result["scores"][jkey] = scores[i]
        if isinstance(scores[i], dict) and "overall" in scores[i]:
            overall_scores.append(float(scores[i]["overall"]))
    
    result["average_overall"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    return result

async def run_tournament(rounds=3):
    """Run full tournament — all 39 beings, all scenarios, all judges."""
    print(f"\n🏛️ CHDDIA² COLOSSEUM v2 — TOURNAMENT START")
    print(f"   {len(BEINGS)} beings × {rounds} rounds × 5 judges")
    print(f"   Total evaluations: {len(BEINGS) * rounds * 5}")
    print(f"{'='*60}\n")
    
    all_results = []
    start = time.time()
    
    for round_num in range(1, rounds + 1):
        print(f"\n🔔 ROUND {round_num}/{rounds}")
        round_start = time.time()
        
        # Run all beings in parallel (batched to avoid rate limits)
        batch_size = 10
        round_results = []
        
        for i in range(0, len(BEINGS), batch_size):
            batch = BEINGS[i:i+batch_size]
            tasks = []
            for being in batch:
                scenario = SCENARIOS.get(being["id"])
                if scenario:
                    tasks.append(run_round(being, scenario, round_num))
            
            batch_results = await asyncio.gather(*tasks)
            round_results.extend(batch_results)
            print(f"   Batch {i//batch_size + 1}: {len(batch_results)} beings scored")
        
        all_results.extend(round_results)
        
        # Print round summary
        round_time = time.time() - round_start
        print(f"\n   ⏱️ Round {round_num} complete in {round_time:.1f}s")
        
        # Top 5 of the round
        sorted_results = sorted(round_results, key=lambda x: x["average_overall"], reverse=True)
        print(f"\n   🏆 TOP 5 THIS ROUND:")
        for j, r in enumerate(sorted_results[:5]):
            print(f"   {j+1}. {r['being_title']} ({r['area']}) — {r['average_overall']:.2f}")
        
        # Bottom 3
        print(f"\n   📉 BOTTOM 3:")
        for r in sorted_results[-3:]:
            print(f"   • {r['being_title']} ({r['area']}) — {r['average_overall']:.2f}")
    
    total_time = time.time() - start
    
    # Final leaderboard
    being_averages = {}
    for r in all_results:
        bid = r["being_id"]
        if bid not in being_averages:
            being_averages[bid] = {"title": r["being_title"], "area": r["area"], "scores": []}
        being_averages[bid]["scores"].append(r["average_overall"])
    
    leaderboard = []
    for bid, data in being_averages.items():
        avg = sum(data["scores"]) / len(data["scores"])
        leaderboard.append({"id": bid, "title": data["title"], "area": data["area"], "average": avg})
    
    leaderboard.sort(key=lambda x: x["average"], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"🏛️ FINAL LEADERBOARD — {len(BEINGS)} beings, {rounds} rounds")
    print(f"   Total time: {total_time:.1f}s | Evaluations: {len(all_results) * 5}")
    print(f"{'='*60}")
    
    for i, entry in enumerate(leaderboard):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        print(f"{medal} {i+1:2d}. {entry['title']:40s} | {entry['area']:30s} | {entry['average']:.2f}")
    
    # Save results
    results_file = RESULTS_DIR / f"tournament_{int(time.time())}.json"
    with results_file.open("w", encoding="utf-8") as f:
        json.dump({
            "leaderboard": leaderboard,
            "rounds": rounds,
            "total_beings": len(BEINGS),
            "total_evaluations": len(all_results) * 5,
            "total_time": total_time,
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to {results_file}")
    
    # Save leaderboard summary
    with (RESULTS_DIR / "leaderboard_latest.json").open("w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)
    
    return leaderboard

if __name__ == "__main__":
    asyncio.run(run_tournament(rounds=3))
