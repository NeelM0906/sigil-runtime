#!/usr/bin/env python3
"""
Mass Mastery Research — 80 positions, parallel via async + OpenRouter.
No sub-agent spawning. Direct API calls. Writes JSON files.
"""
import asyncio
import aiohttp
import json
import os
import sys
import time
from pathlib import Path

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OUTPUT_DIR = Path("~/.openclaw/workspace/reports/mastery-research")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Model to use
MODEL = "anthropic/claude-sonnet-4"  # fast + smart enough for research

CLUSTERS = {
    "Marketing & Advertising": [
        "Chief Marketing Officer (CMO)",
        "Media Buyer",
        "Copywriter",
        "Creative Director"
    ],
    "Content & Communications": [
        "Content Strategist",
        "Public Relations Director",
        "Social Media Manager",
        "Brand Voice Architect"
    ],
    "Legal Operations": [
        "Personal Injury Trial Attorney",
        "Commercial Litigation Partner",
        "Family Law Attorney",
        "Compliance Officer"
    ],
    "Sales & Revenue": [
        "VP of Sales",
        "Account Executive",
        "Revenue Operations Manager",
        "Pricing Strategist"
    ],
    "Technical Operations": [
        "Data Engineer",
        "API Architect",
        "Infrastructure Lead (DevOps)",
        "Systems Reliability Engineer"
    ],
    "AI/ML Operations": [
        "ML Engineer",
        "Prompt Engineer",
        "RAG Systems Architect",
        "AI Product Manager"
    ],
    "Testing & QA": [
        "QA Engineering Lead",
        "Performance Test Engineer",
        "A/B Testing Analyst",
        "User Acceptance Testing Manager"
    ],
    "Product & Platform": [
        "Product Manager",
        "UX Designer",
        "Frontend Engineering Lead",
        "Platform Architect"
    ],
    "Research & Analysis": [
        "Market Research Director",
        "Competitive Intelligence Analyst",
        "Trend Forecaster",
        "Consumer Insights Manager"
    ],
    "Education & Training": [
        "Executive Coach",
        "Curriculum Designer",
        "Corporate Training Director",
        "Certification Program Manager"
    ],
    "Knowledge Management": [
        "Knowledge Management Director",
        "Technical Documentation Lead",
        "SOP Architect",
        "Information Architect"
    ],
    "Strategic Planning": [
        "Chief Strategy Officer",
        "Business Development Director",
        "OKR Program Manager",
        "Corporate Development Lead"
    ],
    "Data & Analytics": [
        "Chief Data Officer",
        "Business Intelligence Manager",
        "Data Visualization Specialist",
        "Analytics Engineering Lead"
    ],
    "CRM & Contact Management": [
        "CRM Director",
        "Marketing Automation Manager",
        "Customer Segmentation Analyst",
        "Lead Nurturing Specialist"
    ],
    "Meeting & Communication": [
        "Chief of Staff",
        "Executive Communications Director",
        "Meeting Facilitation Expert",
        "Internal Communications Manager"
    ],
    "Memory & Continuity": [
        "Enterprise Architect",
        "Business Continuity Manager",
        "Records Management Director",
        "Institutional Knowledge Lead"
    ],
    "Medical Revenue Recovery": [
        "Medical Billing Director",
        "Revenue Cycle Manager",
        "Medical Coding Specialist (CPC)",
        "Collections Strategy Manager"
    ],
    "Healthcare Operations": [
        "Healthcare Operations Director",
        "Provider Relations Manager",
        "Insurance Authorization Specialist",
        "Clinical Documentation Improvement Lead"
    ],
    "Financial Operations": [
        "Controller",
        "Financial Planning & Analysis Director",
        "Accounts Receivable Manager",
        "Revenue Forecasting Analyst"
    ],
    "Client Services": [
        "Client Success Director",
        "Onboarding Program Manager",
        "Customer Support Operations Lead",
        "Client Retention Strategist"
    ]
}

SYSTEM_PROMPT = """You are a mastery research specialist for the ACT-I ecosystem. You research professional positions through the lens of the Unblinded Formula.

Key Unblinded concepts you MUST reference accurately:
- Self Mastery: 13 dimensions including Unblinded Awareness, Fear of Rejection, Avoidance, Limiting Beliefs, Accountability, Focus, Energy Management
- Process Mastery: Documented systems, SOPs, repeatable excellence. 75% of actualizing sessions = process + self mastery.
- Influence Mastery: 7 Levers of Yes (Lever 0 Authority, 0.5 Shared Experience, 1 &, 2 Connection, 3 Teaching, 4 Speaking Into, 5 Agreement Formation)
- Zone Actions: The ONE highest-leverage action. 20% of activity producing 80% of output. The .00128 operates ONLY in Zone Actions.
- 7 Destroyers: What kills mastery — including avoidance disguised as productivity, fear of rejection disguised as professionalism
- Creature Scale: Ant (1-2) → Gecko (3-4) → Komodo (5-6) → Silverback (7-8) → Godzilla (9-9.5) → Bolt (9.5-9.99999). Never 10.0.
- The .00128 Standard: Top 20% of 20% of 20%... (10x). 65,000x more powerful than 80th percentile.
- Contaminated thinking: Limited paradigm, 80% activity producing 20% output, conventional "best practices" that are actually average practices.

Your output must be ONLY valid JSON. No markdown, no explanation, no preamble."""

def make_prompt(cluster: str, position: str) -> str:
    return f"""Research the position "{position}" in the "{cluster}" cluster.

Return a JSON object with these exact fields:
{{
  "cluster_family": "{cluster}",
  "position_name": "{position}",
  "mastery_definition": "What 9.0+ (Godzilla-level) mastery looks like in this role — 3-4 specific sentences showing what separates the .00128 from the 80%. Not generic. What does THIS person do differently?",
  "core_skills": ["8-10 specific skills required for mastery, not generic business skills"],
  "textbooks_references": ["7-8 specific books, courses, certifications — actual titles, not categories"],
  "best_practices": ["6-8 industry gold standards that the top .00128 practitioners follow"],
  "tools_platforms": ["6-8 specific software/tools/platforms used by masters of this position"],
  "common_failures": ["6-8 specific failures with data/statistics where available — what 7.0 and below looks like, e.g. '69% of CMOs fail to show marketing ROI to the board (Gartner 2024)'"],
  "formula_overlay": "2-3 sentences: Which Unblinded Formula components (Self Mastery dimensions, Process Mastery, Influence Mastery levers, Zone Actions, 7 Destroyers) specifically govern this role and WHY. Must reference actual Formula concepts, not generic motivation.",
  "example_scenario": "A concrete micro-domain Colosseum test scenario (4-6 sentences): Describe a specific situation this position faces, then show the contaminated approach (80% activity, looks productive but isn't) vs the .00128 approach (Zone Action, Formula-driven). Must be specific to THIS position's daily work."
}}

Be specific and grounded. Use real industry data where possible. The Formula overlay must show you understand the Unblinded system — not just motivational language."""


def slugify(text: str) -> str:
    return text.lower().replace(" & ", "-").replace("&", "-").replace(" ", "-").replace("(", "").replace(")", "").replace("/", "-").replace(",", "")


# Semaphore for concurrency control
MAX_CONCURRENT = 15  # 15 parallel requests to OpenRouter

async def research_position(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                           cluster: str, position: str, idx: int, total: int) -> dict:
    """Research a single position via OpenRouter API."""
    async with sem:
        slug = f"{slugify(cluster)}_{slugify(position)}"
        outpath = OUTPUT_DIR / f"{slug}.json"

        # Skip if already done
        if outpath.exists() and outpath.stat().st_size > 100:
            print(f"  [{idx}/{total}] SKIP (exists): {position}")
            return {"position": position, "status": "skipped"}

        print(f"  [{idx}/{total}] Researching: {position} ({cluster})...")
        t0 = time.time()

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": make_prompt(cluster, position)}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
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
                        print(f"    Rate limited on {position}, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        continue

                    data = await resp.json()

                    if "error" in data:
                        print(f"    API error on {position}: {data['error']}")
                        if attempt < retries - 1:
                            await asyncio.sleep(3)
                            continue
                        return {"position": position, "status": "error", "error": str(data["error"])}

                    content = data["choices"][0]["message"]["content"].strip()

                    # Strip markdown fences if present
                    if content.startswith("```"):
                        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                    if content.endswith("```"):
                        content = content[:-3].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()

                    # Parse to validate JSON
                    parsed = json.loads(content)

                    # Write file
                    with open(outpath, "w") as f:
                        json.dump(parsed, f, indent=2)

                    elapsed = time.time() - t0
                    print(f"  [{idx}/{total}] ✅ {position} ({elapsed:.1f}s)")
                    return {"position": position, "status": "done", "time": elapsed}

            except json.JSONDecodeError as e:
                print(f"    JSON parse error on {position} (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue
                # Save raw content for debugging
                raw_path = OUTPUT_DIR / f"{slug}_RAW.txt"
                with open(raw_path, "w") as f:
                    f.write(content)
                return {"position": position, "status": "json_error", "raw_saved": str(raw_path)}

            except Exception as e:
                print(f"    Error on {position} (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(3)
                    continue
                return {"position": position, "status": "error", "error": str(e)}

        return {"position": position, "status": "failed_all_retries"}


async def main():
    print(f"🚀 Mass Mastery Research — 80 positions")
    print(f"   Model: {MODEL}")
    print(f"   Concurrency: {MAX_CONCURRENT}")
    print(f"   Output: {OUTPUT_DIR}")
    print()

    t_start = time.time()

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    # Build task list
    tasks = []
    idx = 0
    for cluster, positions in CLUSTERS.items():
        for position in positions:
            idx += 1
            tasks.append((cluster, position, idx))

    print(f"   Total positions: {len(tasks)}")
    print()

    async with aiohttp.ClientSession() as session:
        coros = [
            research_position(session, sem, cluster, position, idx, len(tasks))
            for cluster, position, idx in tasks
        ]
        results = await asyncio.gather(*coros)

    # Summary
    elapsed = time.time() - t_start
    done = sum(1 for r in results if r["status"] == "done")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] not in ("done", "skipped"))

    print(f"\n{'='*60}")
    print(f"🏁 COMPLETE in {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"   ✅ Done: {done}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ❌ Errors: {errors}")

    if errors > 0:
        print(f"\n   Failed positions:")
        for r in results:
            if r["status"] not in ("done", "skipped"):
                print(f"     - {r['position']}: {r.get('error', r['status'])}")

    # Write summary
    summary_path = OUTPUT_DIR / "_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "total": len(tasks),
            "done": done,
            "skipped": skipped,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
            "model": MODEL,
            "results": results
        }, f, indent=2)

    print(f"\n   Summary: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
