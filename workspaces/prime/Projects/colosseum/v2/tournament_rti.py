"""
CHDDIA² Colosseum v2 — Enhanced Tournament Engine with RTI Scoring Architect
=============================================================================

Tournament engine with mandatory RTI (Relative Truth Index) scoring protocols:
- Mandatory "consider the opposite" analysis for ALL judge decisions
- Context calibration requiring complete fact explanation  
- Threshold enforcement preventing scores without full justification
- Conflict detection and resolution mechanisms

Author: RTI Scoring Architect (Subagent)
Date: 2026-02-23
"""

import json
import os
import time
import asyncio
from typing import Dict, List, Any
from openai import AsyncOpenAI
from rti_scoring_architect import rti_enhanced_judge_response

client = AsyncOpenAI()

# Load data
with open("./workspaces/prime/Projects/colosseum/v2/data/beings.json") as f:
    BEINGS = json.load(f)
with open("./workspaces/prime/Projects/colosseum/v2/data/judges.json") as f:
    JUDGES = json.load(f)
with open("./workspaces/prime/Projects/colosseum/v2/data/scenarios.json") as f:
    SCENARIOS = json.load(f)

RESULTS_DIR = "./workspaces/prime/Projects/colosseum/v2/data/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

async def generate_response(being: Dict[str, Any], scenario: Dict[str, Any]) -> str:
    """Have a being respond to its scenario."""
    prompt = f"""SCENARIO: {scenario['title']}
COMPANY: {scenario['company']}
SITUATION: {scenario['situation']}
PERSON: {json.dumps(scenario['person'])}
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
        return f"[ERROR: {e}]"

async def run_round_with_rti(being: Dict[str, Any], 
                           scenario: Dict[str, Any], 
                           round_num: int) -> Dict[str, Any]:
    """
    Run one being through one scenario with all 5 judges using RTI protocols.
    
    Every score goes through:
    1. "Consider the opposite" analysis
    2. Context calibration 
    3. Threshold enforcement
    4. Conflict resolution
    """
    
    print(f"  📝 {being['title']} responding to {scenario['title']}")
    
    # Generate response
    response = await generate_response(being, scenario)
    
    # Score with all 5 judges using RTI protocols
    judge_tasks = []
    for jkey, jdata in JUDGES.items():
        judge_tasks.append(rti_enhanced_judge_response(jkey, jdata, being, scenario, response))
    
    print(f"  🎯 Scoring {being['title']} with RTI protocols...")
    scores = await asyncio.gather(*judge_tasks)
    judge_keys = list(JUDGES.keys())
    
    # Compile results with RTI metadata
    result = {
        "being_id": being["id"],
        "being_title": being["title"],
        "area": being["area"],
        "scenario": scenario["title"],
        "round": round_num,
        "response": response,
        "scores": {},
        "rti_summary": {},
        "timestamp": time.time()
    }
    
    # Process scores and RTI metadata
    valid_scores = []
    invalidated_scores = []
    
    for i, jkey in enumerate(judge_keys):
        score_data = scores[i]
        result["scores"][jkey] = score_data
        
        # Track RTI validation status
        rti_status = score_data.get("rti_status", "UNKNOWN")
        if rti_status == "VALIDATED":
            valid_scores.append(float(score_data.get("overall", 0.0)))
            print(f"    ✅ {jkey}: {score_data.get('overall', 0.0):.2f} (RTI VALIDATED)")
        else:
            invalidated_scores.append(jkey)
            print(f"    ❌ {jkey}: INVALIDATED - {score_data.get('feedback', 'RTI Protocol Violation')}")
    
    # Calculate RTI-validated average
    result["rti_summary"] = {
        "total_judges": len(judge_keys),
        "validated_scores": len(valid_scores),
        "invalidated_scores": len(invalidated_scores),
        "invalidated_judge_ids": invalidated_scores,
        "validation_rate": len(valid_scores) / len(judge_keys),
        "average_validated_score": sum(valid_scores) / len(valid_scores) if valid_scores else 0.0,
        "rti_protocol_version": "RTI-1.0"
    }
    
    result["average_overall"] = result["rti_summary"]["average_validated_score"]
    
    return result

async def run_rti_tournament(rounds: int = 3) -> List[Dict[str, Any]]:
    """
    Run full tournament with mandatory RTI scoring protocols.
    
    ALL judge decisions must pass:
    - "Consider the opposite" analysis
    - Context calibration
    - Threshold enforcement  
    - Conflict resolution
    
    Scores failing RTI protocols are INVALIDATED.
    """
    
    print(f"\n🏛️ CHDDIA² COLOSSEUM v2 — RTI ENHANCED TOURNAMENT")
    print(f"   {len(BEINGS)} beings × {rounds} rounds × 5 judges")
    print(f"   🔬 RTI Protocol: Mandatory Opposition Analysis + Context Calibration")
    print(f"   ❌ INVALID scores automatically rejected")
    print(f"{'='*80}\n")
    
    all_results = []
    start = time.time()
    
    for round_num in range(1, rounds + 1):
        print(f"\n🔔 ROUND {round_num}/{rounds} — RTI PROTOCOLS ACTIVE")
        round_start = time.time()
        
        # Run beings in smaller batches to manage RTI processing load
        batch_size = 5  # Reduced due to RTI overhead
        round_results = []
        
        for i in range(0, len(BEINGS), batch_size):
            batch = BEINGS[i:i+batch_size]
            tasks = []
            
            for being in batch:
                scenario = SCENARIOS.get(being["id"])
                if scenario:
                    tasks.append(run_round_with_rti(being, scenario, round_num))
            
            print(f"\n  📊 Processing batch {i//batch_size + 1} with RTI protocols...")
            batch_results = await asyncio.gather(*tasks)
            round_results.extend(batch_results)
            
            # RTI validation summary for batch
            total_validations = sum(r["rti_summary"]["validated_scores"] for r in batch_results)
            total_possible = sum(r["rti_summary"]["total_judges"] for r in batch_results)
            validation_rate = total_validations / total_possible if total_possible > 0 else 0.0
            
            print(f"    🎯 RTI Validation Rate: {validation_rate:.1%} ({total_validations}/{total_possible})")
        
        all_results.extend(round_results)
        
        # Round summary with RTI metrics
        round_time = time.time() - round_start
        print(f"\n   ⏱️ Round {round_num} complete in {round_time:.1f}s")
        
        # Top 5 of the round (RTI validated scores only)
        valid_results = [r for r in round_results if r["rti_summary"]["validation_rate"] > 0.0]
        sorted_results = sorted(valid_results, key=lambda x: x["average_overall"], reverse=True)
        
        print(f"\n   🏆 TOP 5 THIS ROUND (RTI Validated):")
        for j, r in enumerate(sorted_results[:5]):
            validation_rate = r["rti_summary"]["validation_rate"]
            print(f"   {j+1}. {r['being_title']} ({r['area']}) — {r['average_overall']:.2f} (RTI: {validation_rate:.1%})")
        
        # RTI Protocol Performance Summary
        round_validations = sum(r["rti_summary"]["validated_scores"] for r in round_results)
        round_total = sum(r["rti_summary"]["total_judges"] for r in round_results)
        round_validation_rate = round_validations / round_total if round_total > 0 else 0.0
        
        print(f"\n   🔬 RTI PROTOCOL ROUND SUMMARY:")
        print(f"     • Total Judgments: {round_total}")
        print(f"     • RTI Validated: {round_validations}")
        print(f"     • Invalidated: {round_total - round_validations}")
        print(f"     • Validation Rate: {round_validation_rate:.1%}")
    
    total_time = time.time() - start
    
    # Final leaderboard with RTI metrics
    being_averages = {}
    being_rti_stats = {}
    
    for r in all_results:
        bid = r["being_id"]
        if bid not in being_averages:
            being_averages[bid] = {"title": r["being_title"], "area": r["area"], "scores": []}
            being_rti_stats[bid] = {"validations": 0, "total_judgments": 0}
        
        being_averages[bid]["scores"].append(r["average_overall"])
        being_rti_stats[bid]["validations"] += r["rti_summary"]["validated_scores"]
        being_rti_stats[bid]["total_judgments"] += r["rti_summary"]["total_judges"]
    
    leaderboard = []
    for bid, data in being_averages.items():
        avg = sum(data["scores"]) / len(data["scores"])
        rti_rate = being_rti_stats[bid]["validations"] / being_rti_stats[bid]["total_judgments"]
        
        leaderboard.append({
            "id": bid, 
            "title": data["title"], 
            "area": data["area"], 
            "average": avg,
            "rti_validation_rate": rti_rate,
            "total_validations": being_rti_stats[bid]["validations"],
            "total_judgments": being_rti_stats[bid]["total_judgments"]
        })
    
    leaderboard.sort(key=lambda x: (x["rti_validation_rate"], x["average"]), reverse=True)
    
    # Tournament Summary
    print(f"\n{'='*80}")
    print(f"🏛️ RTI ENHANCED FINAL LEADERBOARD")
    print(f"   {len(BEINGS)} beings, {rounds} rounds with RTI Protocol enforcement")
    print(f"   Total time: {total_time:.1f}s")
    print(f"{'='*80}")
    
    total_validations = sum(being_rti_stats[bid]["validations"] for bid in being_rti_stats)
    total_judgments = sum(being_rti_stats[bid]["total_judgments"] for bid in being_rti_stats)
    overall_validation_rate = total_validations / total_judgments if total_judgments > 0 else 0.0
    
    print(f"\n🔬 TOURNAMENT RTI METRICS:")
    print(f"   • Total Judgments: {total_judgments}")
    print(f"   • RTI Validated: {total_validations}")
    print(f"   • Invalidated: {total_judgments - total_validations}")
    print(f"   • Overall Validation Rate: {overall_validation_rate:.1%}")
    
    print(f"\n📊 FINAL RANKINGS (sorted by RTI validation rate, then score):")
    for i, entry in enumerate(leaderboard):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        print(f"{medal} {i+1:2d}. {entry['title']:35s} | {entry['area']:25s} | {entry['average']:.2f} | RTI: {entry['rti_validation_rate']:.1%}")
    
    # Save enhanced results with RTI metadata
    results_file = f"{RESULTS_DIR}/tournament_rti_{int(time.time())}.json"
    with open(results_file, "w") as f:
        json.dump({
            "leaderboard": leaderboard,
            "rounds": rounds,
            "total_beings": len(BEINGS),
            "rti_protocol_version": "RTI-1.0",
            "rti_metrics": {
                "total_judgments": total_judgments,
                "validated_judgments": total_validations,
                "invalidated_judgments": total_judgments - total_validations,
                "overall_validation_rate": overall_validation_rate
            },
            "total_time": total_time,
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 RTI Enhanced results saved to {results_file}")
    
    # Save RTI leaderboard
    with open(f"{RESULTS_DIR}/leaderboard_rti_latest.json", "w") as f:
        json.dump(leaderboard, f, indent=2)
    
    return leaderboard

if __name__ == "__main__":
    print("🚀 Starting RTI Enhanced Tournament...")
    asyncio.run(run_rti_tournament(rounds=2))  # Reduced rounds due to RTI processing overhead