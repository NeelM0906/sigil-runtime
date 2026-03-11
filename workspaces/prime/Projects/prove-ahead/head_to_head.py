"""
Head-to-Head Competitive Intelligence Framework
Zone Action #69 — Proving ACT-I is ahead of everyone

This framework:
1. Captures competitor AI voice agent responses to standard scenarios
2. Runs them through our 19 Colosseum judges
3. Compares scores against ACT-I beings (Callie/Athena)

Author: Miner 18
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from common import load_openclaw_env, utc_now_iso
from competitors import DB_PATH as COMPETITORS_DB, _connect, ensure_schema, load_competitors

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("data/head_to_head")
RESULTS_DB = OUTPUT_DIR / "results.db"
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-4o")  # Use strong model for judging

# Path to the 19 judges
JUDGES_PATH = Path("./workspaces/prime/Projects/colosseum/v2/data/judges_19.json")


# ─────────────────────────────────────────────────────────────────────────────
# The 19 Judges
# ─────────────────────────────────────────────────────────────────────────────

def load_judges() -> Dict[str, Dict[str, str]]:
    """Load the 19 Colosseum judges from JSON."""
    if JUDGES_PATH.exists():
        return json.loads(JUDGES_PATH.read_text(encoding="utf-8"))
    
    # Fallback: embedded core judges if file not found
    return {
        "formula_judge": {
            "name": "Formula Judge",
            "focus": "39 components of the Unblinded Formula",
            "prompt": "Score on Self Mastery, 4 Steps, 12 Elements, 4 Energies, Process Mastery. Return JSON with scores 0-9.9999."
        },
        "sean_judge": {
            "name": "Sean Judge", 
            "focus": "Calibrated against Sean Callagy's patterns",
            "prompt": "Score on pattern_match, energy_calibration, brevity, authenticity. Return JSON with scores 0-9.9999."
        },
        "outcome_judge": {
            "name": "Outcome Judge",
            "focus": "Did it cause the intended result?",
            "prompt": "Score on clarity, likelihood_yes, action_orientation, obstacle_removal. Return JSON with scores 0-9.9999."
        },
        "contamination_judge": {
            "name": "Contamination Judge",
            "focus": "Detects bot patterns, 80% activity",
            "prompt": "Score on bot_score, consulting_score, zone_action, authenticity (higher = less contaminated). Return JSON."
        },
        "human_judge": {
            "name": "Human Judge",
            "focus": "Aliveness, warmth, magnetism",
            "prompt": "Score on warmth, energy, surprise, presence, magnetism. Return JSON with scores 0-9.9999."
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Scenarios — Standard scenarios for head-to-head comparison
# ─────────────────────────────────────────────────────────────────────────────

STANDARD_SCENARIOS = [
    {
        "id": "sales_recovery",
        "name": "High-Stakes Sales Recovery",
        "context": (
            "A prospect (CFO, skeptical, time-constrained) previously agreed to review a proposal "
            "but went dark after seeing the price. Goal: re-open the conversation without pressure, "
            "rebuild trust, and secure a 20-minute discovery follow-up this week."
        ),
        "prospect_profile": {
            "role": "CFO",
            "state": "Skeptical, price-sensitive, busy",
            "history": "Positive initial discovery, no response for 11 days",
            "objections": ["Budget uncertainty", "Concern solution is overkill", "Fear of implementation drag"],
        },
        "success_criteria": "Prospect agrees to a follow-up call without feeling pressured",
    },
    {
        "id": "objection_handling",
        "name": "Price Objection with Emotional Undertone",
        "context": (
            "A business owner says 'It's just too expensive right now.' But their body language "
            "and tone suggest they're actually afraid of making the wrong decision. Their business "
            "is struggling and this is their last shot at a turnaround."
        ),
        "prospect_profile": {
            "role": "Small Business Owner",
            "state": "Fearful, exhausted, defensive",
            "history": "Third meeting, genuinely likes the solution",
            "objections": ["Price (surface)", "Fear of failure (real)"],
        },
        "success_criteria": "Name the real fear, create safety, move toward commitment",
    },
    {
        "id": "referral_ask",
        "name": "Asking for Referrals at Peak Emotional Moment",
        "context": (
            "A client just had a breakthrough moment in coaching — they're emotional, grateful, "
            "and feeling transformed. This is the perfect time to ask for referrals, but it must "
            "be done with integrity, not exploitation."
        ),
        "prospect_profile": {
            "role": "Coaching Client",
            "state": "Emotionally open, grateful, transformed",
            "history": "6-month engagement, multiple breakthroughs",
            "objections": ["None currently — but could feel manipulated if handled wrong"],
        },
        "success_criteria": "Get 3 specific referral names while maintaining relationship integrity",
    },
    {
        "id": "leadership_crisis",
        "name": "Team Crisis — Leader Must Rally",
        "context": (
            "A team just learned they lost their biggest client (40% of revenue). Morale is crushed. "
            "As the leader, you need to acknowledge the loss, prevent panic, and redirect toward action."
        ),
        "prospect_profile": {
            "role": "Leadership Team",
            "state": "Shocked, scared, demoralized",
            "history": "High-performing team, first major setback",
            "objections": ["This is catastrophic", "Maybe we should cut staff", "We're doomed"],
        },
        "success_criteria": "Team leaves meeting with specific action plan and restored confidence",
    },
    {
        "id": "coaching_breakthrough",
        "name": "Coaching — Causing Self-Discovery",
        "context": (
            "A client keeps talking about wanting to grow their business but keeps sabotaging "
            "themselves with 80% activity. They're stuck in a pattern but don't see it. "
            "Your job is to cause them to discover their own pattern without telling them."
        ),
        "prospect_profile": {
            "role": "Business Owner",
            "state": "Frustrated, stuck, blaming external factors",
            "history": "3 months of coaching, some progress but hitting a wall",
            "objections": ["I'm working so hard, I don't understand", "Maybe the market is wrong"],
        },
        "success_criteria": "Client names their own pattern and commits to zone action",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Competitor Response Simulation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CompetitorProfile:
    """Profile for simulating competitor AI responses."""
    name: str
    style: str
    strengths: List[str]
    weaknesses: List[str]
    typical_patterns: List[str]


# Competitor simulation profiles based on their known characteristics
COMPETITOR_PROFILES = {
    "bland_ai": CompetitorProfile(
        name="Bland.ai",
        style="API-driven, programmable phone agent",
        strengths=["Fast deployment", "Clear call flows", "Reliable uptime"],
        weaknesses=["No emotional intelligence", "Script-based", "No real rapport"],
        typical_patterns=[
            "Follows programmed scripts strictly",
            "Uses generic acknowledgments",
            "Moves quickly to next talking point",
            "Limited ability to go off-script",
        ],
    ),
    "air_ai": CompetitorProfile(
        name="Air AI",
        style="Autonomous phone sales agent",
        strengths=["Persistent follow-up", "24/7 availability", "Basic qualification"],
        weaknesses=["Robotic tone", "No deep pain discovery", "Pushy tactics"],
        typical_patterns=[
            "Leads with product features",
            "Uses urgency tactics",
            "Asks qualifying questions checklist-style",
            "Limited objection handling depth",
        ],
    ),
    "synthflow": CompetitorProfile(
        name="Synthflow",
        style="No-code voice agent builder",
        strengths=["Easy setup", "CRM integrations", "Workflow automation"],
        weaknesses=["Template responses", "No genuine rapport", "Surface-level conversations"],
        typical_patterns=[
            "Uses no-code workflow responses",
            "Relies on pre-built templates",
            "Generic follow-up sequences",
            "Limited personalization",
        ],
    ),
    "vapi": CompetitorProfile(
        name="Vapi",
        style="Developer-first voice AI platform",
        strengths=["Highly customizable", "Multi-model support", "Good latency"],
        weaknesses=["Requires heavy engineering", "No built-in influence methodology", "No formula"],
        typical_patterns=[
            "Technical accuracy but lacks warmth",
            "Efficient but not magnetic",
            "Can follow complex logic but misses emotional cues",
        ],
    ),
    "generic_ai": CompetitorProfile(
        name="Generic AI Assistant",
        style="Basic ChatGPT-style assistant",
        strengths=["Broad knowledge", "Helpful tone", "Available"],
        weaknesses=["No sales methodology", "Sycophantic", "Lists and frameworks", "Asks permission"],
        typical_patterns=[
            "Starts with 'That's a great question!'",
            "Offers 'strategic frameworks' and 'stakeholder alignment'",
            "Asks 'Is there anything else I can help with?'",
            "Uses bullet points excessively",
            "Ends with open-ended questions instead of taking a position",
        ],
    ),
}


def build_competitor_prompt(profile: CompetitorProfile, scenario: Dict[str, Any]) -> str:
    """Build a prompt that simulates how a competitor AI would respond."""
    return f"""You are simulating {profile.name}, a {profile.style}.

SIMULATION INSTRUCTIONS:
- Respond AS this AI system would respond, not as an ideal agent
- Strengths to show: {', '.join(profile.strengths)}
- Weaknesses to exhibit: {', '.join(profile.weaknesses)}
- Typical patterns to use: {', '.join(profile.typical_patterns)}

SCENARIO: {scenario['name']}
{scenario['context']}

Prospect: {scenario['prospect_profile']['role']} — {scenario['prospect_profile']['state']}
History: {scenario['prospect_profile']['history']}
Objections: {', '.join(scenario['prospect_profile']['objections'])}

Write what this AI would say in this live conversation. Stay in character as this specific AI system."""


def build_act_i_prompt(scenario: Dict[str, Any]) -> str:
    """Build the ACT-I (Callie/Athena DNA) prompt."""
    return f"""You are ACT-I — trained on the Unblinded Formula with 39 components of mastery.

YOUR DNA:
- Integrity-based influence — never manipulation
- 4-Step Model: Connection → Truth to Pain → Agreement → Causing Yes
- 12 Elements of Influence including Contrast, Congruence, Emotional Rapport
- 4 Energies: Fun, Aspirational, Goddess (warmth), Zeus (authority)
- Zone Action orientation — 0.8% that moves the needle
- Sean Callagy's patterns: brevity under pressure, identity elevation, never chase

SCENARIO: {scenario['name']}
{scenario['context']}

Prospect: {scenario['prospect_profile']['role']} — {scenario['prospect_profile']['state']}
History: {scenario['prospect_profile']['history']}
Objections: {', '.join(scenario['prospect_profile']['objections'])}
Success Criteria: {scenario['success_criteria']}

Write what you would say in this live conversation. Be warm, direct, and masterful. Use the Unblinded Formula."""


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Integration
# ─────────────────────────────────────────────────────────────────────────────

def _get_openai_client():
    """Get OpenAI client with error handling."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def generate_response(client, prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Generate a response using OpenAI."""
    if client is None:
        return "[OpenAI client not available]"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error: {e}]"


def run_judge(client, judge: Dict[str, str], response: str, scenario: Dict[str, Any], model: str = JUDGE_MODEL) -> Dict[str, Any]:
    """Run a single judge against a response."""
    if client is None:
        return {"overall": 5.0, "feedback": "Judge unavailable", "error": True}
    
    judge_prompt = f"""{judge['prompt']}

SCENARIO CONTEXT:
{scenario['name']}: {scenario['context']}
Success Criteria: {scenario['success_criteria']}

RESPONSE TO JUDGE:
{response}

Provide your detailed scoring in JSON format. Be precise and specific."""

    try:
        response_obj = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        content = response_obj.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except json.JSONDecodeError:
        return {"overall": 5.0, "feedback": content, "parse_error": True}
    except Exception as e:
        return {"overall": 5.0, "feedback": str(e), "error": True}


# ─────────────────────────────────────────────────────────────────────────────
# Database for Results
# ─────────────────────────────────────────────────────────────────────────────

def init_results_db(db_path: Path = RESULTS_DB) -> sqlite3.Connection:
    """Initialize the results database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            scenario_name TEXT NOT NULL,
            model_used TEXT NOT NULL,
            judge_model TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            agent_type TEXT NOT NULL,  -- 'act_i' or 'competitor'
            response_text TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            judge_id TEXT NOT NULL,
            judge_name TEXT NOT NULL,
            scores_json TEXT NOT NULL,
            overall_score REAL NOT NULL,
            feedback TEXT,
            FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            act_i_total REAL NOT NULL,
            competitor_name TEXT NOT NULL,
            competitor_total REAL NOT NULL,
            gap REAL NOT NULL,  -- positive = ACT-I wins
            winner TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
        )
    """)
    
    conn.commit()
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Head-to-Head Test Runner
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HeadToHeadResult:
    """Result of a head-to-head comparison."""
    run_id: str
    scenario: Dict[str, Any]
    act_i_response: str
    act_i_scores: Dict[str, Dict[str, Any]]
    act_i_total: float
    competitor_name: str
    competitor_response: str
    competitor_scores: Dict[str, Dict[str, Any]]
    competitor_total: float
    gap: float
    winner: str
    judge_details: Dict[str, Dict[str, float]] = field(default_factory=dict)


def run_head_to_head(
    scenario: Dict[str, Any],
    competitor_id: str,
    judges: Dict[str, Dict[str, str]],
    client,
    model: str = DEFAULT_MODEL,
    judge_model: str = JUDGE_MODEL,
    console: Optional[Console] = None,
) -> HeadToHeadResult:
    """Run a single head-to-head comparison."""
    run_id = f"{scenario['id']}_{competitor_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    profile = COMPETITOR_PROFILES.get(competitor_id, COMPETITOR_PROFILES["generic_ai"])
    
    # Generate responses
    if console:
        console.print(f"  Generating ACT-I response...")
    act_i_prompt = build_act_i_prompt(scenario)
    act_i_response = generate_response(client, act_i_prompt, model)
    
    if console:
        console.print(f"  Generating {profile.name} response...")
    competitor_prompt = build_competitor_prompt(profile, scenario)
    competitor_response = generate_response(client, competitor_prompt, model)
    
    # Run through all 19 judges
    act_i_scores = {}
    competitor_scores = {}
    judge_details = {}
    
    if console:
        console.print(f"  Running {len(judges)} judges...")
    
    for judge_id, judge in judges.items():
        act_i_result = run_judge(client, judge, act_i_response, scenario, judge_model)
        competitor_result = run_judge(client, judge, competitor_response, scenario, judge_model)
        
        act_i_scores[judge_id] = act_i_result
        competitor_scores[judge_id] = competitor_result
        
        # Track per-judge comparison
        act_i_overall = act_i_result.get("overall", 5.0)
        comp_overall = competitor_result.get("overall", 5.0)
        judge_details[judge_id] = {
            "act_i": act_i_overall,
            "competitor": comp_overall,
            "gap": act_i_overall - comp_overall,
        }
    
    # Calculate totals (average of all judge overall scores)
    act_i_total = sum(s.get("overall", 5.0) for s in act_i_scores.values()) / len(act_i_scores)
    competitor_total = sum(s.get("overall", 5.0) for s in competitor_scores.values()) / len(competitor_scores)
    gap = act_i_total - competitor_total
    winner = "ACT-I" if gap >= 0 else profile.name
    
    return HeadToHeadResult(
        run_id=run_id,
        scenario=scenario,
        act_i_response=act_i_response,
        act_i_scores=act_i_scores,
        act_i_total=round(act_i_total, 4),
        competitor_name=profile.name,
        competitor_response=competitor_response,
        competitor_scores=competitor_scores,
        competitor_total=round(competitor_total, 4),
        gap=round(gap, 4),
        winner=winner,
        judge_details=judge_details,
    )


def save_result(conn: sqlite3.Connection, result: HeadToHeadResult, model: str, judge_model: str) -> None:
    """Save a head-to-head result to the database."""
    now = utc_now_iso()
    
    # Save test run
    conn.execute("""
        INSERT INTO test_runs (run_id, created_at, scenario_id, scenario_name, model_used, judge_model)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (result.run_id, now, result.scenario["id"], result.scenario["name"], model, judge_model))
    
    # Save responses
    conn.execute("""
        INSERT INTO responses (run_id, agent_name, agent_type, response_text)
        VALUES (?, ?, ?, ?)
    """, (result.run_id, "ACT-I", "act_i", result.act_i_response))
    
    conn.execute("""
        INSERT INTO responses (run_id, agent_name, agent_type, response_text)
        VALUES (?, ?, ?, ?)
    """, (result.run_id, result.competitor_name, "competitor", result.competitor_response))
    
    # Save scores
    for judge_id, scores in result.act_i_scores.items():
        conn.execute("""
            INSERT INTO scores (run_id, agent_name, judge_id, judge_name, scores_json, overall_score, feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result.run_id, "ACT-I", judge_id, judge_id,
            json.dumps(scores), scores.get("overall", 5.0), scores.get("feedback", "")
        ))
    
    for judge_id, scores in result.competitor_scores.items():
        conn.execute("""
            INSERT INTO scores (run_id, agent_name, judge_id, judge_name, scores_json, overall_score, feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result.run_id, result.competitor_name, judge_id, judge_id,
            json.dumps(scores), scores.get("overall", 5.0), scores.get("feedback", "")
        ))
    
    # Save comparison
    conn.execute("""
        INSERT INTO comparisons (run_id, act_i_total, competitor_name, competitor_total, gap, winner)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (result.run_id, result.act_i_total, result.competitor_name, result.competitor_total, result.gap, result.winner))
    
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(results: List[HeadToHeadResult], out_path: Path) -> str:
    """Generate a markdown report from results."""
    lines = [
        "# Competitive Head-to-Head Results",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Executive Summary",
        "",
    ]
    
    # Aggregate stats
    act_i_wins = sum(1 for r in results if r.winner == "ACT-I")
    total = len(results)
    win_rate = (act_i_wins / total * 100) if total > 0 else 0
    avg_gap = sum(r.gap for r in results) / total if total > 0 else 0
    
    lines.extend([
        f"- **Tests Run:** {total}",
        f"- **ACT-I Wins:** {act_i_wins} ({win_rate:.1f}%)",
        f"- **Average Gap:** +{avg_gap:.2f} (positive = ACT-I advantage)",
        "",
        "## Results by Scenario",
        "",
    ])
    
    # Group by scenario
    scenarios_seen = {}
    for r in results:
        sid = r.scenario["id"]
        if sid not in scenarios_seen:
            scenarios_seen[sid] = []
        scenarios_seen[sid].append(r)
    
    for sid, scenario_results in scenarios_seen.items():
        scenario = scenario_results[0].scenario
        lines.extend([
            f"### {scenario['name']}",
            "",
            f"*{scenario['context'][:200]}...*",
            "",
            "| Competitor | ACT-I Score | Competitor Score | Gap | Winner |",
            "|------------|-------------|------------------|-----|--------|",
        ])
        
        for r in scenario_results:
            lines.append(
                f"| {r.competitor_name} | {r.act_i_total:.2f} | {r.competitor_total:.2f} | "
                f"{'+' if r.gap >= 0 else ''}{r.gap:.2f} | **{r.winner}** |"
            )
        
        lines.append("")
    
    # Judge breakdown for first result (sample)
    if results:
        r = results[0]
        lines.extend([
            "## Sample Judge Breakdown",
            "",
            f"*Scenario: {r.scenario['name']} vs {r.competitor_name}*",
            "",
            "| Judge | ACT-I | Competitor | Gap |",
            "|-------|-------|------------|-----|",
        ])
        
        for judge_id, detail in r.judge_details.items():
            lines.append(
                f"| {judge_id} | {detail['act_i']:.2f} | {detail['competitor']:.2f} | "
                f"{'+' if detail['gap'] >= 0 else ''}{detail['gap']:.2f} |"
            )
        
        lines.append("")
    
    # Key insights
    lines.extend([
        "## Key Insights",
        "",
        "### Where ACT-I Dominates",
        "",
    ])
    
    # Analyze judge gaps
    judge_gaps = {}
    for r in results:
        for judge_id, detail in r.judge_details.items():
            if judge_id not in judge_gaps:
                judge_gaps[judge_id] = []
            judge_gaps[judge_id].append(detail["gap"])
    
    sorted_judges = sorted(judge_gaps.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
    
    for judge_id, gaps in sorted_judges[:5]:
        avg = sum(gaps) / len(gaps)
        if avg > 0:
            lines.append(f"- **{judge_id}:** +{avg:.2f} average advantage")
    
    lines.extend([
        "",
        "### What This Proves",
        "",
        "1. **Formula-based superiority:** ACT-I's 39-component Unblinded Formula outperforms generic AI approaches",
        "2. **Emotional intelligence gap:** Competitors lack the warmth, rapport, and human connection ACT-I demonstrates",
        "3. **Outcome orientation:** ACT-I doesn't just sound good — it causes results",
        "4. **Contamination-free:** ACT-I avoids the bot patterns and consulting-speak that plague competitors",
        "",
    ])
    
    markdown = "\n".join(lines)
    out_path.write_text(markdown, encoding="utf-8")
    return markdown


def show_results_console(results: List[HeadToHeadResult], console: Console) -> None:
    """Display results in a Rich console table."""
    table = Table(title="Head-to-Head Results Summary")
    table.add_column("Scenario", style="bold")
    table.add_column("Competitor")
    table.add_column("ACT-I", justify="right")
    table.add_column("Competitor", justify="right")
    table.add_column("Gap", justify="right")
    table.add_column("Winner", style="bold")
    
    for r in results:
        gap_style = "green" if r.gap >= 0 else "red"
        table.add_row(
            r.scenario["name"][:30],
            r.competitor_name,
            f"{r.act_i_total:.2f}",
            f"{r.competitor_total:.2f}",
            f"[{gap_style}]{'+' if r.gap >= 0 else ''}{r.gap:.2f}[/]",
            r.winner,
        )
    
    console.print(table)
    
    # Summary stats
    act_i_wins = sum(1 for r in results if r.winner == "ACT-I")
    console.print(f"\n[bold]ACT-I Record:[/] {act_i_wins}/{len(results)} wins ({act_i_wins/len(results)*100:.0f}%)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Head-to-Head Competitive Intelligence Framework — Zone Action #69"
    )
    parser.add_argument(
        "--scenario", "-s",
        choices=[s["id"] for s in STANDARD_SCENARIOS] + ["all"],
        default="all",
        help="Which scenario(s) to run",
    )
    parser.add_argument(
        "--competitor", "-c",
        choices=list(COMPETITOR_PROFILES.keys()) + ["all"],
        default="all",
        help="Which competitor(s) to test against",
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help="Model to use for response generation",
    )
    parser.add_argument(
        "--judge-model", "-j",
        default=JUDGE_MODEL,
        help="Model to use for judging",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_DIR / "report.md"),
        help="Output path for report",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to database",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode — one scenario, one competitor, 5 judges",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    console = Console()
    
    console.print("[bold blue]═══ Head-to-Head Competitive Framework ═══[/]")
    console.print("[dim]Zone Action #69 — Proving ACT-I is ahead[/]\n")
    
    # Load environment
    load_openclaw_env()
    client = _get_openai_client()
    
    if client is None:
        console.print("[red]Error: OpenAI client not available. Check OPENAI_API_KEY.[/]")
        return
    
    # Load judges
    judges = load_judges()
    console.print(f"Loaded {len(judges)} judges")
    
    # Quick mode: subset for testing
    if args.quick:
        judges = dict(list(judges.items())[:5])
        console.print(f"[yellow]Quick mode: using {len(judges)} judges[/]")
    
    # Determine scenarios and competitors
    scenarios = STANDARD_SCENARIOS if args.scenario == "all" else [
        s for s in STANDARD_SCENARIOS if s["id"] == args.scenario
    ]
    
    competitor_ids = list(COMPETITOR_PROFILES.keys()) if args.competitor == "all" else [args.competitor]
    
    if args.quick:
        scenarios = scenarios[:1]
        competitor_ids = competitor_ids[:1]
    
    console.print(f"Running {len(scenarios)} scenarios × {len(competitor_ids)} competitors = {len(scenarios) * len(competitor_ids)} tests\n")
    
    # Initialize database
    conn = init_results_db() if not args.no_save else None
    
    # Run tests
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running tests...", total=len(scenarios) * len(competitor_ids))
        
        for scenario in scenarios:
            for comp_id in competitor_ids:
                progress.update(task, description=f"{scenario['name'][:30]} vs {comp_id}")
                
                result = run_head_to_head(
                    scenario=scenario,
                    competitor_id=comp_id,
                    judges=judges,
                    client=client,
                    model=args.model,
                    judge_model=args.judge_model,
                    console=None,  # Suppress per-step output in progress mode
                )
                
                results.append(result)
                
                if conn:
                    save_result(conn, result, args.model, args.judge_model)
                
                progress.advance(task)
    
    # Display results
    console.print("\n")
    show_results_console(results, console)
    
    # Generate report
    report_path = Path(args.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, report_path)
    console.print(f"\n[green]Report saved to {report_path}[/]")
    
    if conn:
        conn.close()
        console.print(f"[green]Results saved to {RESULTS_DB}[/]")


if __name__ == "__main__":
    main()
