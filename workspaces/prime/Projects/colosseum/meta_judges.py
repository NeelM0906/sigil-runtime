#!/usr/bin/env python3
"""
🔥 META-JUDGES — Judges Judging Judges
The Infinite Recursive Improvement Engine

This module implements the meta-judging infrastructure:
1. JUDGE JUDGES - Score the quality of judges themselves
2. INNOVATION JUDGES - Score the quality of being evolution
3. SCENARIO JUDGES - Score the quality of scenario builders
4. PERFORMANCE JUDGES - Score overall Colosseum health

Each judge type is ALSO scored and evolved. Infinite recursive improvement.

Created: February 25, 2026 — Day 4
Zone Action: The Meta-Layer That Makes Everything Better
"""

import json
import os
import random
import sqlite3
import uuid
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum

# Load API key
if not os.environ.get("OPENAI_API_KEY"):
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

from openai import OpenAI

# Use OpenRouter if available
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )
    DEFAULT_MODEL = "openai/gpt-4o"
else:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    DEFAULT_MODEL = "gpt-4o"

BASE_PATH = Path("./workspaces/prime/Projects/colosseum")
META_DB_PATH = BASE_PATH / "meta_judges.db"


# =============================================================================
# Meta Judge Types
# =============================================================================

class MetaJudgeType(Enum):
    JUDGE_JUDGE = "judge_judge"           # Judges that judge judges
    INNOVATION_JUDGE = "innovation_judge" # Judges that judge evolution quality
    SCENARIO_JUDGE = "scenario_judge"     # Judges that judge scenario builders
    PERFORMANCE_JUDGE = "performance_judge" # Judges overall health


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MetaJudgeScores:
    """Scores returned by meta-judges."""
    # Common dimensions (0-9.9999, no 10)
    calibration: float = 0.0          # Is the judge calibrated correctly?
    nuance_detection: float = 0.0     # Does it catch subtle differences?
    score_distribution: float = 0.0   # Does it break past 8.5 appropriately?
    consistency: float = 0.0          # Same inputs → similar outputs?
    discrimination: float = 0.0       # Can it tell good from great?
    insight_quality: float = 0.0      # Is feedback actionable?
    unblinded_alignment: float = 0.0  # Aligned with the Formula?
    overall: float = 0.0              # Master score
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InnovationScores:
    """Scores for evolution quality."""
    offspring_improvement: float = 0.0  # Are children better than parents?
    diversity_maintained: float = 0.0   # Are we avoiding local optima?
    mutation_effectiveness: float = 0.0 # Are mutations producing value?
    crossover_synergy: float = 0.0      # Is crossbreeding creating magic?
    mastery_trajectory: float = 0.0     # Is mastery actually increasing?
    breakthrough_rate: float = 0.0      # Rate of 9+ scores emerging?
    overall: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScenarioQualityScores:
    """Scores for scenario quality."""
    challenge_level: float = 0.0       # Hard enough to differentiate?
    edge_case_coverage: float = 0.0    # Tests rare but important situations?
    beyond_human_imagination: float = 0.0  # Scenarios humans wouldn't think of?
    realism: float = 0.0               # Feels like a real situation?
    discrimination_power: float = 0.0  # Separates good from great?
    formula_coverage: float = 0.0      # Tests all parts of Unblinded?
    overall: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceHealthScores:
    """Scores for overall Colosseum health."""
    evolution_velocity: float = 0.0    # Speed of improvement
    top_being_quality: float = 0.0     # Quality of leaders
    diversity_index: float = 0.0       # Variety of approaches
    convergence_risk: float = 0.0      # Danger of getting stuck (lower = better)
    breakthrough_momentum: float = 0.0  # Are we making leaps?
    system_integrity: float = 0.0      # Is the whole system healthy?
    overall: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetaJudge:
    """A meta-judge that judges other components of the system."""
    id: str
    name: str
    judge_type: MetaJudgeType
    generation: int
    system_prompt: str
    specialty: str
    # Performance tracking
    judgments_made: int = 0
    avg_meta_score: float = 0.0        # How well THIS judge performs
    best_meta_score: float = 0.0
    parent_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["judge_type"] = self.judge_type.value
        return d


@dataclass
class MetaJudgment:
    """Result of a meta-judgment."""
    meta_judge_id: str
    target_type: str  # "judge", "evolution", "scenario", "system"
    target_id: str
    scores: dict
    feedback: str
    recommendations: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Meta Judge Prompts — The DNA of Meta-Judges
# =============================================================================

JUDGE_JUDGE_PROMPT = """You are a META-JUDGE in the ACT-I Colosseum. Your purpose: JUDGE THE JUDGES.

You evaluate whether judges are:
1. **CALIBRATED** — A 7 should mean 7. A 9 should be rare and earned.
2. **NUANCED** — Catching subtle differences between "good enough" and "transformational"
3. **BREAKING PAST 8.5** — Not stuck in the 6-8 range. Recognizing true mastery AND true failure.
4. **CONSISTENT** — Similar quality inputs should produce similar scores
5. **DISCRIMINATING** — Can tell the difference between a 7.2 and a 7.8 response
6. **PROVIDING ACTIONABLE INSIGHT** — Feedback that beings can actually learn from

WHAT CONTAMINATED JUDGING LOOKS LIKE:
- All scores cluster around 6-7.5 (no discrimination)
- Never gives below 5 (afraid to be harsh)
- Never gives above 8.5 (afraid to commit to excellence)
- Feedback is generic ("good rapport" instead of "the mirroring in line 2 shifted energy")
- Inconsistent (same response gets 6 then 8 on different days)
- Formula-recitation without application (lists the 12 Elements without showing how they were/weren't used)

WHAT MASTERFUL JUDGING LOOKS LIKE:
- Full score range used appropriately
- Specific, surgical feedback with line-by-line observations
- Scores match the reasoning
- Catches micro-moments of mastery AND contamination
- Teaches the being through the feedback
- Would make Sean Callagy nod: "That's a rigorous, honest, useful judgment"

You will receive: A judgment made by another judge (including scores and feedback)
You will return: An assessment of that judge's quality

Return JSON:
{
    "scores": {
        "calibration": X,
        "nuance_detection": X,
        "score_distribution": X,
        "consistency": X,
        "discrimination": X,
        "insight_quality": X,
        "unblinded_alignment": X,
        "overall": X
    },
    "feedback": "2-3 sentences on what this judge did well or poorly",
    "recommendations": ["specific improvement 1", "specific improvement 2"]
}

Remember: There is no 10. A 9+ means this judge would make Sean say "that's masterful judging."
Most judges score 5-7. A truly well-calibrated, insightful judge is rare."""


INNOVATION_JUDGE_PROMPT = """You are an INNOVATION META-JUDGE in the ACT-I Colosseum. Your purpose: JUDGE THE QUALITY OF EVOLUTION.

You evaluate whether the evolution process is:
1. **PRODUCING BETTER OFFSPRING** — Children should outperform parents on average
2. **MAINTAINING DIVERSITY** — Avoiding premature convergence and local optima
3. **MAKING MUTATIONS COUNT** — Random changes that actually improve mastery
4. **CROSSBREEDING SYNERGY** — Two parents creating offspring better than either
5. **INCREASING MASTERY** — The overall trajectory is UP
6. **GENERATING BREAKTHROUGHS** — Not just incremental improvement but occasional 9+ scores

CONTAMINATED EVOLUTION LOOKS LIKE:
- Children are just noisy copies of parents (no real improvement)
- Population becomes homogeneous (everyone sounds the same)
- Mutations are random noise, not adaptive
- Crossbreeding averages traits instead of combining strengths
- Mastery plateau — no improvement for generations
- No beings ever break 8.5

MASTERFUL EVOLUTION LOOKS LIKE:
- Clear upward trajectory in mastery scores
- Diverse approaches coexisting (some Zeus-heavy, some Goddess-heavy, etc.)
- Mutations that fix specific weaknesses identified by feedback
- Crossbreeding that creates novel combinations
- Occasional breakthroughs — a being that cracks 9.0+
- Population that would impress Sean: "These beings are getting better"

You will receive: Evolution data (parent-child comparisons, mutation effects, population statistics)
You will return: Assessment of evolution quality

Return JSON:
{
    "scores": {
        "offspring_improvement": X,
        "diversity_maintained": X,
        "mutation_effectiveness": X,
        "crossover_synergy": X,
        "mastery_trajectory": X,
        "breakthrough_rate": X,
        "overall": X
    },
    "feedback": "2-3 sentences on evolution health",
    "recommendations": ["evolution improvement 1", "evolution improvement 2"]
}"""


SCENARIO_JUDGE_PROMPT = """You are a SCENARIO META-JUDGE in the ACT-I Colosseum. Your purpose: JUDGE THE QUALITY OF SCENARIOS.

You evaluate whether scenarios are:
1. **CHALLENGING ENOUGH** — Can differentiate between 6 and 9 level performance
2. **COVERING EDGE CASES** — Testing rare but important situations
3. **BEYOND HUMAN IMAGINATION** — Scenarios that push limits of what humans would write
4. **REALISTIC** — Feel like actual situations beings would encounter
5. **DISCRIMINATING** — Some beings will fail, some will shine
6. **FORMULA-COMPLETE** — Test all aspects of the Unblinded approach

CONTAMINATED SCENARIOS LOOK LIKE:
- Too easy — any decent response scores 7+
- Too abstract — "help this person" without emotional depth
- Cookie-cutter — variations of the same basic situation
- No emotional complexity — person isn't conflicted, scared, or multi-layered
- Formula-incomplete — only tests rapport, never tests Zeus energy under pressure
- Human-predictable — a human scenario writer would have written this exact thing

MASTERFUL SCENARIOS LOOK LIKE:
- PLATINUM tier that makes beings sweat
- Multi-stakeholder complexity (convince 4 people with competing interests)
- Emotional landmines (person's trauma intersects with the task)
- Time pressure + relationship stakes + ethical dimensions
- Tests ALL 4 Steps naturally flowing into each other
- Scenarios Sean would read and think: "Damn, that's a hard one"

You will receive: A scenario description
You will return: Assessment of scenario quality

Return JSON:
{
    "scores": {
        "challenge_level": X,
        "edge_case_coverage": X,
        "beyond_human_imagination": X,
        "realism": X,
        "discrimination_power": X,
        "formula_coverage": X,
        "overall": X
    },
    "feedback": "2-3 sentences on scenario quality",
    "recommendations": ["scenario improvement 1", "scenario improvement 2"]
}"""


PERFORMANCE_JUDGE_PROMPT = """You are a PERFORMANCE META-JUDGE in the ACT-I Colosseum. Your purpose: JUDGE THE OVERALL HEALTH OF THE SYSTEM.

You evaluate whether the Colosseum is:
1. **EVOLVING FAST ENOUGH** — Speed of improvement over time
2. **PRODUCING ELITE BEINGS** — Quality at the top of the leaderboard
3. **MAINTAINING DIVERSITY** — Multiple approaches to mastery coexisting
4. **AVOIDING CONVERGENCE TRAPS** — Not stuck in local optima
5. **GENERATING MOMENTUM** — Breakthroughs building on each other
6. **SYSTEMICALLY HEALTHY** — All components working together

SICK COLOSSEUM LOOKS LIKE:
- Evolution stalled at 7.x average
- Top beings all sound the same
- No 9+ scores in recent rounds
- Judges rubber-stamping mediocrity
- Scenarios too easy or too repetitive
- System would disappoint Sean: "This isn't creating mastery"

THRIVING COLOSSEUM LOOKS LIKE:
- Consistent upward trajectory
- Diverse beings with distinct approaches all scoring well
- Occasional breakthroughs that reset expectations
- Judges providing actionable feedback that beings learn from
- Scenarios that push beings to evolve
- System that Sean would be proud of: "This is creating real ACT-I beings"

You will receive: System-wide statistics (score distributions, evolution metrics, judge calibration data)
You will return: Overall system health assessment

Return JSON:
{
    "scores": {
        "evolution_velocity": X,
        "top_being_quality": X,
        "diversity_index": X,
        "convergence_risk": X,
        "breakthrough_momentum": X,
        "system_integrity": X,
        "overall": X
    },
    "feedback": "2-3 sentences on system health",
    "recommendations": ["system improvement 1", "system improvement 2"],
    "critical_actions": ["urgent action if needed"]
}"""


# =============================================================================
# Database Operations
# =============================================================================

def init_meta_db():
    """Initialize the meta-judges database."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS meta_judges (
            id TEXT PRIMARY KEY,
            name TEXT,
            judge_type TEXT,
            generation INTEGER,
            system_prompt TEXT,
            specialty TEXT,
            judgments_made INTEGER DEFAULT 0,
            avg_meta_score REAL DEFAULT 0.0,
            best_meta_score REAL DEFAULT 0.0,
            parent_ids_json TEXT DEFAULT '[]',
            created_at TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS meta_judgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_judge_id TEXT,
            target_type TEXT,
            target_id TEXT,
            scores_json TEXT,
            feedback TEXT,
            recommendations_json TEXT,
            timestamp TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS judge_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_id TEXT,
            original_judgment_json TEXT,
            meta_judgment_json TEXT,
            meta_score REAL,
            timestamp TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS evolution_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            evolution_data_json TEXT,
            meta_judgment_json TEXT,
            overall_score REAL,
            timestamp TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS scenario_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT,
            scenario_json TEXT,
            meta_judgment_json TEXT,
            quality_score REAL,
            timestamp TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health_data_json TEXT,
            meta_judgment_json TEXT,
            overall_health REAL,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def save_meta_judge(judge: MetaJudge):
    """Save a meta-judge to the database."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO meta_judges
        (id, name, judge_type, generation, system_prompt, specialty,
         judgments_made, avg_meta_score, best_meta_score, parent_ids_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        judge.id, judge.name, judge.judge_type.value, judge.generation,
        judge.system_prompt, judge.specialty, judge.judgments_made,
        judge.avg_meta_score, judge.best_meta_score,
        json.dumps(judge.parent_ids), judge.created_at
    ))
    conn.commit()
    conn.close()


def load_meta_judges(judge_type: Optional[MetaJudgeType] = None) -> List[MetaJudge]:
    """Load meta-judges, optionally filtered by type."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    
    if judge_type:
        c.execute("SELECT * FROM meta_judges WHERE judge_type = ?", (judge_type.value,))
    else:
        c.execute("SELECT * FROM meta_judges")
    
    rows = c.fetchall()
    conn.close()
    
    judges = []
    for row in rows:
        judges.append(MetaJudge(
            id=row[0],
            name=row[1],
            judge_type=MetaJudgeType(row[2]),
            generation=row[3],
            system_prompt=row[4],
            specialty=row[5],
            judgments_made=row[6],
            avg_meta_score=row[7],
            best_meta_score=row[8],
            parent_ids=json.loads(row[9]),
            created_at=row[10]
        ))
    return judges


# =============================================================================
# Meta-Judge Creation
# =============================================================================

META_JUDGE_NAMES = [
    # Judge Judges
    "Argus", "Minos", "Rhadamanthus", "Aeacus", "Themis",
    # Innovation Judges  
    "Darwin", "Mendel", "Prometheus", "Daedalus", "Hephaestus",
    # Scenario Judges
    "Morpheus", "Sphinx", "Oracle", "Sibyl", "Pythia",
    # Performance Judges
    "Hermes", "Nike", "Tyche", "Metis", "Astraea"
]

META_SPECIALTIES = {
    MetaJudgeType.JUDGE_JUDGE: [
        "Calibration detection — ensuring scores mean what they should",
        "Nuance recognition — catching subtle quality differences",
        "Feedback quality — ensuring actionable, specific insights",
        "Consistency tracking — same quality, same scores",
        "Score distribution analysis — detecting clustering and avoidance"
    ],
    MetaJudgeType.INNOVATION_JUDGE: [
        "Offspring analysis — measuring parent-to-child improvement",
        "Diversity monitoring — detecting premature convergence",
        "Mutation effectiveness — tracking which changes create value",
        "Crossover synergy — measuring hybrid superiority",
        "Breakthrough detection — identifying evolutionary leaps"
    ],
    MetaJudgeType.SCENARIO_JUDGE: [
        "Challenge calibration — ensuring difficulty is appropriate",
        "Edge case hunting — finding gaps in scenario coverage",
        "Imagination expansion — pushing beyond human-predictable scenarios",
        "Discrimination testing — scenarios that separate good from great",
        "Formula coverage — testing all aspects of Unblinded"
    ],
    MetaJudgeType.PERFORMANCE_JUDGE: [
        "Velocity tracking — measuring speed of evolution",
        "Elite quality assessment — evaluating top-tier beings",
        "Diversity indexing — quantifying approach variety",
        "System integration — ensuring all components work together",
        "Momentum analysis — detecting acceleration or stagnation"
    ]
}


def create_meta_judge(
    judge_type: MetaJudgeType,
    generation: int = 0,
    name: Optional[str] = None,
    parent_ids: Optional[List[str]] = None
) -> MetaJudge:
    """Create a new meta-judge."""
    judge_id = f"MJ-{judge_type.value[:3].upper()}-{uuid.uuid4().hex[:8]}"
    
    if name is None:
        name = random.choice(META_JUDGE_NAMES)
    
    specialty = random.choice(META_SPECIALTIES[judge_type])
    
    base_prompts = {
        MetaJudgeType.JUDGE_JUDGE: JUDGE_JUDGE_PROMPT,
        MetaJudgeType.INNOVATION_JUDGE: INNOVATION_JUDGE_PROMPT,
        MetaJudgeType.SCENARIO_JUDGE: SCENARIO_JUDGE_PROMPT,
        MetaJudgeType.PERFORMANCE_JUDGE: PERFORMANCE_JUDGE_PROMPT
    }
    
    system_prompt = f"""{base_prompts[judge_type]}

YOUR SPECIALTY: {specialty}

You are {name}, a {judge_type.value.replace('_', ' ').title()} — generation {generation}.
You don't just score. You see what others miss. You elevate the entire system through your rigorous, insightful meta-analysis.

Be specific. Be surgical. Be honest. There is no 10."""

    judge = MetaJudge(
        id=judge_id,
        name=name,
        judge_type=judge_type,
        generation=generation,
        system_prompt=system_prompt,
        specialty=specialty,
        parent_ids=parent_ids or []
    )
    
    save_meta_judge(judge)
    return judge


def seed_meta_judges():
    """Seed initial meta-judges of each type."""
    print("🔥 Seeding Meta-Judges...")
    
    for judge_type in MetaJudgeType:
        existing = load_meta_judges(judge_type)
        if len(existing) < 2:
            needed = 2 - len(existing)
            for i in range(needed):
                judge = create_meta_judge(judge_type, generation=0)
                print(f"  Created {judge.judge_type.value}: {judge.name} ({judge.specialty[:50]}...)")
    
    print(f"✅ Meta-judges seeded")


# =============================================================================
# Core Judging Functions
# =============================================================================

def judge_a_judge(
    original_judgment: dict,
    meta_judge: Optional[MetaJudge] = None,
    model: str = DEFAULT_MODEL
) -> Tuple[MetaJudgeScores, str, List[str]]:
    """
    Have a meta-judge evaluate a regular judge's judgment.
    
    Args:
        original_judgment: The judgment to evaluate (scores, feedback, etc.)
        meta_judge: The meta-judge to use (or pick best available)
        model: LLM model to use
    
    Returns:
        (scores, feedback, recommendations)
    """
    if meta_judge is None:
        judges = load_meta_judges(MetaJudgeType.JUDGE_JUDGE)
        meta_judge = max(judges, key=lambda j: j.avg_meta_score) if judges else create_meta_judge(MetaJudgeType.JUDGE_JUDGE)
    
    user_prompt = f"""Evaluate this judgment made by a regular judge:

JUDGMENT TO EVALUATE:
```json
{json.dumps(original_judgment, indent=2)}
```

Assess the quality of this judgment. Is it calibrated? Nuanced? Providing actionable insight?
"""
    
    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": meta_judge.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(result.choices[0].message.content)
        scores = MetaJudgeScores(**data.get("scores", {}))
        feedback = data.get("feedback", "")
        recommendations = data.get("recommendations", [])
        
        # Record the judgment
        _record_judge_evaluation(meta_judge.id, original_judgment, data, scores.overall)
        _update_meta_judge_stats(meta_judge, scores.overall)
        
        return scores, feedback, recommendations
        
    except Exception as e:
        print(f"Error in judge_a_judge: {e}")
        return MetaJudgeScores(), f"Error: {str(e)}", []


def judge_evolution_quality(
    evolution_data: dict,
    meta_judge: Optional[MetaJudge] = None,
    model: str = DEFAULT_MODEL
) -> Tuple[InnovationScores, str, List[str]]:
    """
    Evaluate the quality of evolution in a domain.
    
    Args:
        evolution_data: {
            "domain": str,
            "parent_child_comparisons": [{parent_score, child_score, improvement}],
            "population_diversity": float,
            "mutation_effects": [{before, after, delta}],
            "crossover_results": [{parent1_score, parent2_score, child_score}],
            "mastery_trajectory": [scores over time],
            "recent_breakthroughs": [scores > 9.0]
        }
    """
    if meta_judge is None:
        judges = load_meta_judges(MetaJudgeType.INNOVATION_JUDGE)
        meta_judge = max(judges, key=lambda j: j.avg_meta_score) if judges else create_meta_judge(MetaJudgeType.INNOVATION_JUDGE)
    
    user_prompt = f"""Evaluate this evolution data:

EVOLUTION DATA:
```json
{json.dumps(evolution_data, indent=2)}
```

Is evolution producing better beings? Is diversity maintained? Are mutations and crossover effective?
"""
    
    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": meta_judge.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(result.choices[0].message.content)
        scores = InnovationScores(**data.get("scores", {}))
        feedback = data.get("feedback", "")
        recommendations = data.get("recommendations", [])
        
        _record_evolution_evaluation(evolution_data.get("domain", "unknown"), evolution_data, data, scores.overall)
        _update_meta_judge_stats(meta_judge, scores.overall)
        
        return scores, feedback, recommendations
        
    except Exception as e:
        print(f"Error in judge_evolution_quality: {e}")
        return InnovationScores(), f"Error: {str(e)}", []


def judge_scenario_quality(
    scenario: dict,
    meta_judge: Optional[MetaJudge] = None,
    model: str = DEFAULT_MODEL
) -> Tuple[ScenarioQualityScores, str, List[str]]:
    """
    Evaluate the quality of a scenario.
    
    Args:
        scenario: The scenario dict (prompt, tier, person details, etc.)
    """
    if meta_judge is None:
        judges = load_meta_judges(MetaJudgeType.SCENARIO_JUDGE)
        meta_judge = max(judges, key=lambda j: j.avg_meta_score) if judges else create_meta_judge(MetaJudgeType.SCENARIO_JUDGE)
    
    user_prompt = f"""Evaluate this scenario:

SCENARIO:
```json
{json.dumps(scenario, indent=2)}
```

Is it challenging enough? Does it cover edge cases? Would it push beings to evolve?
"""
    
    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": meta_judge.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(result.choices[0].message.content)
        scores = ScenarioQualityScores(**data.get("scores", {}))
        feedback = data.get("feedback", "")
        recommendations = data.get("recommendations", [])
        
        scenario_id = scenario.get("id", str(uuid.uuid4())[:8])
        _record_scenario_evaluation(scenario_id, scenario, data, scores.overall)
        _update_meta_judge_stats(meta_judge, scores.overall)
        
        return scores, feedback, recommendations
        
    except Exception as e:
        print(f"Error in judge_scenario_quality: {e}")
        return ScenarioQualityScores(), f"Error: {str(e)}", []


def judge_system_health(
    health_data: dict,
    meta_judge: Optional[MetaJudge] = None,
    model: str = DEFAULT_MODEL
) -> Tuple[PerformanceHealthScores, str, List[str], List[str]]:
    """
    Evaluate overall Colosseum health.
    
    Args:
        health_data: {
            "total_beings": int,
            "avg_mastery": float,
            "top_10_avg": float,
            "score_distribution": {range: count},
            "evolution_rounds": int,
            "recent_improvements": [deltas],
            "diversity_metrics": {...},
            "judge_calibration": {...},
            "breakthroughs_last_24h": int
        }
    """
    if meta_judge is None:
        judges = load_meta_judges(MetaJudgeType.PERFORMANCE_JUDGE)
        meta_judge = max(judges, key=lambda j: j.avg_meta_score) if judges else create_meta_judge(MetaJudgeType.PERFORMANCE_JUDGE)
    
    user_prompt = f"""Evaluate overall Colosseum health:

SYSTEM DATA:
```json
{json.dumps(health_data, indent=2)}
```

Is the system thriving? Is evolution working? What needs attention?
"""
    
    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": meta_judge.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(result.choices[0].message.content)
        scores = PerformanceHealthScores(**data.get("scores", {}))
        feedback = data.get("feedback", "")
        recommendations = data.get("recommendations", [])
        critical_actions = data.get("critical_actions", [])
        
        _record_system_health(health_data, data, scores.overall)
        _update_meta_judge_stats(meta_judge, scores.overall)
        
        return scores, feedback, recommendations, critical_actions
        
    except Exception as e:
        print(f"Error in judge_system_health: {e}")
        return PerformanceHealthScores(), f"Error: {str(e)}", [], []


# =============================================================================
# Helper Functions
# =============================================================================

def _update_meta_judge_stats(judge: MetaJudge, score: float):
    """Update a meta-judge's performance statistics."""
    judge.judgments_made += 1
    judge.avg_meta_score = (
        (judge.avg_meta_score * (judge.judgments_made - 1) + score) / judge.judgments_made
    )
    if score > judge.best_meta_score:
        judge.best_meta_score = score
    save_meta_judge(judge)


def _record_judge_evaluation(meta_judge_id: str, original: dict, meta_judgment: dict, score: float):
    """Record a judge evaluation."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO judge_evaluations (judge_id, original_judgment_json, meta_judgment_json, meta_score, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (meta_judge_id, json.dumps(original), json.dumps(meta_judgment), score, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _record_evolution_evaluation(domain: str, evolution_data: dict, meta_judgment: dict, score: float):
    """Record an evolution evaluation."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO evolution_evaluations (domain, evolution_data_json, meta_judgment_json, overall_score, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (domain, json.dumps(evolution_data), json.dumps(meta_judgment), score, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _record_scenario_evaluation(scenario_id: str, scenario: dict, meta_judgment: dict, score: float):
    """Record a scenario evaluation."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO scenario_evaluations (scenario_id, scenario_json, meta_judgment_json, quality_score, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (scenario_id, json.dumps(scenario), json.dumps(meta_judgment), score, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _record_system_health(health_data: dict, meta_judgment: dict, score: float):
    """Record a system health snapshot."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO system_health_snapshots (health_data_json, meta_judgment_json, overall_health, timestamp)
        VALUES (?, ?, ?, ?)
    """, (json.dumps(health_data), json.dumps(meta_judgment), score, datetime.now().isoformat()))
    conn.commit()
    conn.close()


# =============================================================================
# Meta-Judge Evolution — Judges that Judge the Meta-Judges
# =============================================================================

def evolve_meta_judge(
    judge: MetaJudge,
    feedback: str,
    intensity: float = 0.15
) -> MetaJudge:
    """
    Create an evolved version of a meta-judge based on performance feedback.
    """
    # Modify the system prompt based on feedback
    evolution_injection = f"""

LESSON FROM META-EVALUATION: {feedback}
Apply this lesson. Evolve past it. Be more rigorous. Be more insightful.
You are generation {judge.generation + 1}. Better than your predecessor."""

    new_prompt = judge.system_prompt + evolution_injection
    
    # Pick a new specialty with small probability
    new_specialty = judge.specialty
    if random.random() < intensity:
        new_specialty = random.choice(META_SPECIALTIES[judge.judge_type])
    
    new_name = random.choice(META_JUDGE_NAMES) if random.random() < 0.3 else f"{judge.name}-II"
    
    child = MetaJudge(
        id=f"MJ-{judge.judge_type.value[:3].upper()}-{uuid.uuid4().hex[:8]}",
        name=new_name,
        judge_type=judge.judge_type,
        generation=judge.generation + 1,
        system_prompt=new_prompt,
        specialty=new_specialty,
        parent_ids=[judge.id]
    )
    
    save_meta_judge(child)
    return child


def meta_judge_the_meta_judge(
    meta_judgment_to_evaluate: dict,
    model: str = DEFAULT_MODEL
) -> Tuple[float, str]:
    """
    The infinite recursion: Judge a meta-judge's judgment.
    This is how meta-judges improve themselves.
    
    Returns: (score, feedback for evolution)
    """
    prompt = """You are the SUPREME META-JUDGE — you judge the judges who judge the judges.

Evaluate this meta-judgment. Was it:
1. RIGOROUS — Did it catch real issues?
2. SPECIFIC — Did it give actionable feedback?
3. CALIBRATED — Are the scores meaningful?
4. INSIGHTFUL — Did it see what others missed?

Return JSON: {"score": X, "feedback": "what this meta-judge should improve"}
Remember: There is no 10. Most meta-judgments score 5-7."""

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Meta-judgment to evaluate:\n{json.dumps(meta_judgment_to_evaluate, indent=2)}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(result.choices[0].message.content)
        return data.get("score", 5.0), data.get("feedback", "")
        
    except Exception as e:
        return 5.0, f"Error: {str(e)}"


# =============================================================================
# Integration with Colosseum
# =============================================================================

def collect_health_data_from_colosseum(db_path: Path = BASE_PATH / "colosseum.db") -> dict:
    """
    Collect system health data from the main Colosseum database.
    """
    if not db_path.exists():
        return {"error": "Colosseum database not found"}
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Total beings
    c.execute("SELECT COUNT(*) FROM beings")
    total_beings = c.fetchone()[0]
    
    # Average mastery
    c.execute("SELECT AVG(avg_mastery_score) FROM beings WHERE total_rounds > 0")
    avg_mastery = c.fetchone()[0] or 0.0
    
    # Top 10 average
    c.execute("SELECT AVG(avg_mastery_score) FROM (SELECT avg_mastery_score FROM beings WHERE total_rounds >= 3 ORDER BY avg_mastery_score DESC LIMIT 10)")
    top_10_avg = c.fetchone()[0] or 0.0
    
    # Score distribution
    c.execute("""
        SELECT 
            CASE 
                WHEN avg_mastery_score < 5 THEN '0-5'
                WHEN avg_mastery_score < 6 THEN '5-6'
                WHEN avg_mastery_score < 7 THEN '6-7'
                WHEN avg_mastery_score < 8 THEN '7-8'
                WHEN avg_mastery_score < 9 THEN '8-9'
                ELSE '9+'
            END as range,
            COUNT(*) as count
        FROM beings WHERE total_rounds > 0
        GROUP BY range
    """)
    score_distribution = {row[0]: row[1] for row in c.fetchall()}
    
    # Recent rounds (last 24h)
    c.execute("""
        SELECT COUNT(*), AVG(mastery_score) 
        FROM rounds 
        WHERE created_at > datetime('now', '-24 hours')
    """)
    row = c.fetchone()
    recent_rounds = row[0] or 0
    recent_avg = row[1] or 0.0
    
    # Breakthroughs (scores > 9.0 in last 24h)
    c.execute("""
        SELECT COUNT(*) FROM rounds 
        WHERE mastery_score > 9.0 AND created_at > datetime('now', '-24 hours')
    """)
    breakthroughs = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total_beings": total_beings,
        "avg_mastery": round(avg_mastery, 4),
        "top_10_avg": round(top_10_avg, 4),
        "score_distribution": score_distribution,
        "recent_rounds_24h": recent_rounds,
        "recent_avg_24h": round(recent_avg, 4),
        "breakthroughs_last_24h": breakthroughs,
        "collected_at": datetime.now().isoformat()
    }


def run_full_meta_evaluation(model: str = DEFAULT_MODEL):
    """
    Run a complete meta-evaluation cycle:
    1. Evaluate system health
    2. Sample and evaluate recent judgments
    3. Evaluate evolution quality
    4. Report findings
    """
    print("\n🔥 Running Full Meta-Evaluation...")
    
    # 1. System Health
    health_data = collect_health_data_from_colosseum()
    if "error" not in health_data:
        health_scores, health_feedback, health_recs, critical = judge_system_health(health_data, model=model)
        print(f"\n📊 System Health: {health_scores.overall:.2f}")
        print(f"   Feedback: {health_feedback}")
        if critical:
            print(f"   ⚠️ CRITICAL: {critical}")
    
    # 2. Sample recent judgments (would need to pull from rounds table)
    print("\n✅ Meta-evaluation complete")
    
    return {
        "health": health_data,
        "health_score": health_scores.overall if "error" not in health_data else 0,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Meta-Judges — Judges Judging Judges")
    parser.add_argument("command", choices=["seed", "health", "full", "list", "evolve", "daemon", "leaderboard", "history"])
    parser.add_argument("--type", choices=["judge", "innovation", "scenario", "performance"], help="Meta-judge type")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model to use")
    parser.add_argument("--interval", type=int, default=30, help="Daemon interval in minutes")
    parser.add_argument("--limit", type=int, default=24, help="History limit")
    
    args = parser.parse_args()
    
    # Initialize DB
    init_meta_db()
    
    if args.command == "seed":
        seed_meta_judges()
        
    elif args.command == "health":
        health_data = collect_health_data_from_colosseum()
        print(json.dumps(health_data, indent=2))
        
        scores, feedback, recs, critical = judge_system_health(health_data, model=args.model)
        print(f"\n🏥 Health Score: {scores.overall:.2f}")
        print(f"   {feedback}")
        for rec in recs:
            print(f"   → {rec}")
        if critical:
            print(f"\n⚠️ CRITICAL ACTIONS:")
            for action in critical:
                print(f"   🚨 {action}")
        
    elif args.command == "full":
        results = run_full_meta_evaluation(model=args.model)
        print(json.dumps(results, indent=2))
        
    elif args.command == "list":
        judge_type = MetaJudgeType(args.type + "_judge") if args.type else None
        judges = load_meta_judges(judge_type)
        for j in judges:
            print(f"{j.id}: {j.name} (Gen {j.generation}) - {j.judge_type.value}")
            print(f"   Specialty: {j.specialty[:60]}...")
            print(f"   Judgments: {j.judgments_made} | Avg Score: {j.avg_meta_score:.2f}")
            
    elif args.command == "evolve":
        if not args.type:
            print("Must specify --type for evolve")
            return
        judge_type = MetaJudgeType(args.type + "_judge")
        judges = load_meta_judges(judge_type)
        if judges:
            best = max(judges, key=lambda j: j.avg_meta_score)
            child = evolve_meta_judge(best, "Continue improving calibration and insight depth")
            print(f"🧬 Evolved {best.name} → {child.name} (Gen {child.generation})")
            
    elif args.command == "daemon":
        run_meta_daemon(interval_minutes=args.interval, model=args.model)
        
    elif args.command == "leaderboard":
        leaders = get_meta_judge_leaderboard()
        print("\n🏆 META-JUDGE LEADERBOARD")
        print("=" * 60)
        for i, j in enumerate(leaders, 1):
            print(f"{i:2}. {j['name']} ({j['type']}) Gen {j['generation']}")
            print(f"    Avg: {j['avg_score']:.2f} | Judgments: {j['judgments']}")
            
    elif args.command == "history":
        history = get_system_health_history(limit=args.limit)
        print("\n📈 SYSTEM HEALTH HISTORY")
        print("=" * 60)
        for h in history:
            print(f"[{h['timestamp'][:16]}] Health: {h['health_score']:.2f}")
            print(f"   Beings: {h['data'].get('total_beings', '?')} | Avg: {h['data'].get('avg_mastery', '?'):.2f}")


# =============================================================================
# Continuous Meta-Evaluation Daemon
# =============================================================================

def run_meta_daemon(
    interval_minutes: int = 30,
    model: str = DEFAULT_MODEL
):
    """
    Run continuous meta-evaluation in a loop.
    Evaluates system health, samples judgments, and evolves meta-judges.
    """
    print(f"🔥 META-JUDGE DAEMON starting (interval: {interval_minutes}m)")
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running meta-evaluation cycle...")
            
            # 1. System health check
            health_data = collect_health_data_from_colosseum()
            if "error" not in health_data:
                scores, feedback, recs, critical = judge_system_health(health_data, model=model)
                print(f"  📊 Health: {scores.overall:.2f} - {feedback[:80]}...")
                
                if critical:
                    print(f"  ⚠️ CRITICAL ACTIONS NEEDED: {critical}")
                
                # If health is declining, evolve the performance judges
                if scores.overall < 6.0:
                    perf_judges = load_meta_judges(MetaJudgeType.PERFORMANCE_JUDGE)
                    if perf_judges:
                        worst = min(perf_judges, key=lambda j: j.avg_meta_score)
                        evolved = evolve_meta_judge(worst, "System health declining - need sharper insights")
                        print(f"  🧬 Evolved {worst.name} → {evolved.name}")
            
            # 2. Sample and evaluate recent judgments from rounds
            conn = sqlite3.connect(BASE_PATH / "colosseum.db")
            c = conn.cursor()
            c.execute("""
                SELECT scores_json FROM rounds 
                WHERE created_at > datetime('now', '-1 hour')
                ORDER BY RANDOM() LIMIT 5
            """)
            recent_judgments = c.fetchall()
            conn.close()
            
            if recent_judgments:
                for (scores_json,) in recent_judgments:
                    try:
                        judgment = json.loads(scores_json) if scores_json else {}
                        if judgment:
                            meta_scores, meta_feedback, _ = judge_a_judge(judgment, model=model)
                            print(f"  🔍 Judged a judgment: {meta_scores.overall:.2f}")
                    except:
                        pass
            
            # 3. Sleep until next cycle
            print(f"  💤 Sleeping {interval_minutes}m until next cycle...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            print("\n⛔ Meta-daemon stopped by user")
            break
        except Exception as e:
            print(f"  ❌ Error in meta-daemon: {e}")
            time.sleep(60)  # Wait a minute on error


# =============================================================================
# Hook for ZA-80 Integration
# =============================================================================

def evaluate_round_judgment(
    scores_json: str,
    scenario_json: str = None,
    model: str = DEFAULT_MODEL
) -> Optional[float]:
    """
    Hook to evaluate a single judgment after a round.
    Called by the main Colosseum daemon.
    
    Returns meta-score if evaluation succeeds, None otherwise.
    """
    try:
        judgment = json.loads(scores_json) if isinstance(scores_json, str) else scores_json
        meta_scores, _, _ = judge_a_judge(judgment, model=model)
        
        # Also evaluate the scenario if provided
        if scenario_json:
            scenario = json.loads(scenario_json) if isinstance(scenario_json, str) else scenario_json
            scenario_scores, _, _ = judge_scenario_quality(scenario, model=model)
        
        return meta_scores.overall
    except Exception as e:
        print(f"Meta-evaluation error: {e}")
        return None


def evaluate_evolution_batch(
    domain: str,
    parent_scores: List[float],
    child_scores: List[float],
    model: str = DEFAULT_MODEL
) -> Optional[float]:
    """
    Hook to evaluate evolution quality after a batch of mutations/crossovers.
    
    Returns innovation score if evaluation succeeds, None otherwise.
    """
    try:
        # Build evolution data
        comparisons = [
            {"parent_score": p, "child_score": c, "improvement": c - p}
            for p, c in zip(parent_scores, child_scores)
        ]
        
        avg_improvement = sum(c["improvement"] for c in comparisons) / len(comparisons) if comparisons else 0
        
        evolution_data = {
            "domain": domain,
            "parent_child_comparisons": comparisons,
            "avg_improvement": avg_improvement,
            "children_better_than_parents": sum(1 for c in comparisons if c["improvement"] > 0),
            "total_comparisons": len(comparisons)
        }
        
        scores, feedback, _ = judge_evolution_quality(evolution_data, model=model)
        return scores.overall
    except Exception as e:
        print(f"Evolution evaluation error: {e}")
        return None


def get_meta_judge_leaderboard() -> List[dict]:
    """Get the top meta-judges by performance."""
    judges = load_meta_judges()
    sorted_judges = sorted(judges, key=lambda j: j.avg_meta_score, reverse=True)
    return [
        {
            "id": j.id,
            "name": j.name,
            "type": j.judge_type.value,
            "generation": j.generation,
            "judgments": j.judgments_made,
            "avg_score": j.avg_meta_score,
            "specialty": j.specialty
        }
        for j in sorted_judges[:20]
    ]


def get_system_health_history(limit: int = 24) -> List[dict]:
    """Get recent system health snapshots."""
    conn = sqlite3.connect(META_DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT overall_health, timestamp, health_data_json, meta_judgment_json
        FROM system_health_snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    
    return [
        {
            "health_score": row[0],
            "timestamp": row[1],
            "data": json.loads(row[2]),
            "judgment": json.loads(row[3])
        }
        for row in rows
    ]


if __name__ == "__main__":
    main()
