#!/usr/bin/env python3
"""
Refine 80 mastery research JSONs — fill gaps, deepen Formula overlays,
normalize field counts, strengthen scenarios.
"""
import asyncio
import aiohttp
import json
import os
import time
from pathlib import Path

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-sonnet-4"
RESEARCH_DIR = Path("~/.openclaw/workspace/reports/mastery-research")
MAX_CONCURRENT = 12

SYSTEM_PROMPT = """You are a mastery research refinement specialist. You receive an existing position mastery profile and improve it.

Key Unblinded Formula concepts (use PRECISELY):
- Self Mastery (13 dimensions): Unblinded Awareness, Fear of Rejection, Avoidance, Limiting Beliefs, Accountability, Focus, Energy Management, Identity, Emotional Mastery, Time Mastery, Physical Mastery, Financial Mastery, Relationship Mastery
- Process Mastery: Modeling → Time Blocking → Measure/Monitor → Innovate/Optimize. Documented systems. SOPs. Repeatable excellence.
- Influence Mastery — 7 Levers of Yes: Lever 0 (Authority), 0.5 (Shared Experience), 1 (Rapport/&), 2 (Connection), 3 (Teaching/Nurturing), 4 (Speaking Into/Conversion), 5 (Agreement Formation)
- 4-Step Communication Model: Hook → Truth → Pain → Solution
- 7 Destroyers: Fear of Rejection, Avoidance, Limiting Beliefs, Lack of Accountability, Emotional Reactivity, Identity Confusion, Energy Depletion
- Zone Actions: The ONE action in the 20% that produces 80%. The .00128 lives here.
- Creature Scale: Ant(1-2) → Gecko(3-4) → Komodo(5-6) → Silverback(7-8) → Godzilla(9-9.5) → Bolt(9.5-9.99999)
- The .00128: Top 20%^10 = 65,000x more effective than 80th percentile
- 5 Rounds to Attention: People need 5+ touches before real engagement
- 12 Indispensable Elements of Influence: The complete transmission mechanism

Your output must be ONLY valid JSON. No markdown fences, no explanation."""


def diagnose_gaps(entry: dict) -> list[str]:
    """Identify what needs improvement."""
    issues = []
    
    skills = entry.get("core_skills", [])
    books = entry.get("textbooks_references", [])
    tools = entry.get("tools_platforms", [])
    failures = entry.get("common_failures", [])
    formula = entry.get("formula_overlay", "")
    scenario = entry.get("example_scenario", "")
    mastery = entry.get("mastery_definition", "")
    
    # Field count issues
    if len(skills) < 8:
        issues.append(f"core_skills has only {len(skills)}, need 8-10")
    if len(skills) > 10:
        issues.append(f"core_skills has {len(skills)}, trim to best 10")
    if len(books) < 7:
        issues.append(f"textbooks_references has only {len(books)}, need 7-8")
    if len(books) > 8:
        issues.append(f"textbooks_references has {len(books)}, trim to best 8")
    if len(tools) < 6:
        issues.append(f"tools_platforms has only {len(tools)}, need 6-8")
    if len(tools) > 8:
        issues.append(f"tools_platforms has {len(tools)}, trim to best 8")
    if len(failures) < 6:
        issues.append(f"common_failures has only {len(failures)}, need 6-8")
    if len(failures) > 8:
        issues.append(f"common_failures has {len(failures)}, trim to best 8")
    
    # Formula depth
    formula_keywords = ["Self Mastery", "Process Mastery", "Influence Mastery", "Zone Action", 
                       "Lever", "Destroyer", ".00128", "Avoidance", "Fear of Rejection"]
    formula_hits = sum(1 for kw in formula_keywords if kw.lower() in formula.lower())
    if formula_hits < 4:
        issues.append(f"formula_overlay only references {formula_hits}/9 key concepts — needs deeper Formula integration showing WHY these components govern this role")
    if len(formula) < 200:
        issues.append("formula_overlay is too short — expand to 3-4 sentences with specific connections")
    
    # Scenario depth
    if len(scenario) < 300:
        issues.append("example_scenario is too thin — needs specific numbers, timeline, and clear contaminated vs .00128 contrast")
    if "zone action" not in scenario.lower() and "zone" not in scenario.lower():
        issues.append("example_scenario missing explicit Zone Action identification")
    
    # Mastery definition
    if len(mastery) < 150:
        issues.append("mastery_definition too short — needs 3-4 specific sentences")
    if ".00128" not in mastery and "00128" not in mastery:
        issues.append("mastery_definition should reference the .00128 standard")
    
    return issues


def make_refinement_prompt(entry: dict, issues: list[str]) -> str:
    return f"""Here is an existing mastery research profile that needs refinement:

{json.dumps(entry, indent=2)}

ISSUES TO FIX:
{chr(10).join(f"- {issue}" for issue in issues)}

REFINEMENT RULES:
1. Keep ALL existing good content — don't throw away strong entries
2. Add missing items to reach target counts (8-10 skills, 7-8 books, 6-8 tools, 6-8 failures)
3. Trim over-stuffed fields to the BEST entries within target range
4. DEEPEN the formula_overlay — it must explain the INVISIBLE PHYSICS of why specific Formula components govern this role. Not "this role uses Process Mastery" but "the Controller's Zone Action IS the variance analysis because 58% spend time gathering data (Destroyer: Avoidance disguised as thoroughness) instead of the one predictive insight that changes the CFO's next decision"
5. Strengthen example_scenario with specific numbers, timelines, and explicit Zone Action identification
6. Every common_failure should have a stat/data point if possible
7. mastery_definition should reference the .00128 standard

Return the COMPLETE refined JSON object with all fields."""


async def refine_position(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                          fpath: Path, idx: int, total: int) -> dict:
    """Refine a single position."""
    async with sem:
        with open(fpath) as f:
            entry = json.load(f)
        
        position = entry.get("position_name", fpath.stem)
        
        # Diagnose
        issues = diagnose_gaps(entry)
        
        if not issues:
            print(f"  [{idx}/{total}] CLEAN: {position}")
            return {"position": position, "status": "clean", "issues": 0}
        
        print(f"  [{idx}/{total}] Refining: {position} ({len(issues)} issues)...", end=" ", flush=True)
        t0 = time.time()
        
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": make_refinement_prompt(entry, issues)}
            ],
            "temperature": 0.5,
            "max_tokens": 3000
        }
        
        retries = 3
        for attempt in range(retries):
            try:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 429:
                        wait = 5 * (attempt + 1)
                        print(f"rate limited, waiting {wait}s...", end=" ", flush=True)
                        await asyncio.sleep(wait)
                        continue
                    
                    data = await resp.json()
                    
                    if "error" in data:
                        if attempt < retries - 1:
                            await asyncio.sleep(3)
                            continue
                        print(f"❌ API error")
                        return {"position": position, "status": "error", "error": str(data["error"])}
                    
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # Strip markdown fences
                    if content.startswith("```"):
                        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                    if content.endswith("```"):
                        content = content[:-3].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                    
                    refined = json.loads(content)
                    
                    # Validate it still has all required fields
                    required = ["cluster_family", "position_name", "mastery_definition", 
                               "core_skills", "textbooks_references", "best_practices",
                               "tools_platforms", "common_failures", "formula_overlay", "example_scenario"]
                    missing = [k for k in required if k not in refined]
                    if missing:
                        print(f"⚠️ missing fields: {missing}")
                        # Merge back missing fields from original
                        for k in missing:
                            refined[k] = entry[k]
                    
                    # Write refined version
                    with open(fpath, "w") as f:
                        json.dump(refined, f, indent=2)
                    
                    elapsed = time.time() - t0
                    
                    # Check remaining issues
                    remaining = diagnose_gaps(refined)
                    
                    print(f"✅ ({elapsed:.1f}s, {len(issues)}→{len(remaining)} issues)")
                    return {"position": position, "status": "refined", "before": len(issues), 
                            "after": len(remaining), "time": elapsed}
                    
            except json.JSONDecodeError as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue
                print(f"❌ JSON error")
                return {"position": position, "status": "json_error"}
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(3)
                    continue
                print(f"❌ {e}")
                return {"position": position, "status": "error", "error": str(e)}
        
        return {"position": position, "status": "failed"}


async def main():
    print(f"🔧 Mastery Research Refinement Pass")
    print(f"   Model: {MODEL}")
    print(f"   Concurrency: {MAX_CONCURRENT}")
    print()
    
    # Load all files
    files = sorted(RESEARCH_DIR.glob("*.json"))
    files = [f for f in files if f.name != "_summary.json" and not f.name.endswith("_RAW.txt")]
    
    # Pre-diagnose to show scope
    total_issues = 0
    needs_work = 0
    for fpath in files:
        with open(fpath) as f:
            entry = json.load(f)
        issues = diagnose_gaps(entry)
        if issues:
            needs_work += 1
            total_issues += len(issues)
    
    print(f"   Files: {len(files)}")
    print(f"   Need refinement: {needs_work}")
    print(f"   Total issues: {total_issues}")
    print()
    
    t_start = time.time()
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with aiohttp.ClientSession() as session:
        coros = [
            refine_position(session, sem, fpath, idx, len(files))
            for idx, fpath in enumerate(files, 1)
        ]
        results = await asyncio.gather(*coros)
    
    elapsed = time.time() - t_start
    
    refined = sum(1 for r in results if r["status"] == "refined")
    clean = sum(1 for r in results if r["status"] == "clean")
    errors = sum(1 for r in results if r["status"] not in ("refined", "clean"))
    remaining_issues = sum(r.get("after", 0) for r in results if r["status"] == "refined")
    
    print(f"\n{'='*60}")
    print(f"🏁 REFINEMENT COMPLETE in {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"   ✅ Refined: {refined}")
    print(f"   ✨ Already clean: {clean}")
    print(f"   ❌ Errors: {errors}")
    print(f"   📊 Issues before: {total_issues} → after: {remaining_issues}")
    
    if errors:
        print(f"\n   Failed:")
        for r in results:
            if r["status"] not in ("refined", "clean"):
                print(f"     - {r['position']}: {r.get('error', r['status'])}")


if __name__ == "__main__":
    asyncio.run(main())
