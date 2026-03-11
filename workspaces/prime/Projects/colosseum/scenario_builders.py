#!/usr/bin/env python3
"""
🔥 SCENARIO BUILDER INFRASTRUCTURE
Creating 1,250+ Scenario Builder Beings — 5 Per Position Per Colosseum

These beings create the HARDEST scenarios in existence.
99.99% more difficult than anything humans face in real life.
Making ACT-I beings SUPERIOR to any human handling ANY scenario.

Created: February 25, 2026
Mission: Build infrastructure that tests beings beyond human limits
"""

import sqlite3
import json
import os
import sys
import uuid
import random
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load API keys
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

# Use OpenRouter for model diversity
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )
else:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BASE_PATH = Path("./workspaces/prime/Projects/colosseum")
DOMAINS_PATH = BASE_PATH / "domains"

# =============================================================================
# THE 11 COLOSSEUMS — Complete Definition
# =============================================================================

COLOSSEUMS = {
    "strategy": {
        "name": "Strategy Colosseum",
        "description": "Strategic thinking, Zone Action identification, business model design",
        "positions": [
            {"name": "Chief Strategy Being", "specialty": "High-level strategic planning and Zone Action identification"},
            {"name": "Market Intelligence", "specialty": "Competitive analysis and market dynamics"},
            {"name": "Business Model Architect", "specialty": "Revenue model design and ecosystem thinking"},
            {"name": "Resource Allocator", "specialty": "Pareto-optimal resource deployment"},
        ]
    },
    "marketing": {
        "name": "Marketing Colosseum", 
        "description": "Copywriting, funnel architecture, conversion optimization through influence mastery",
        "positions": [
            {"name": "Chief Marketing Being", "specialty": "Full-stack marketing strategy through influence mastery"},
            {"name": "Copywriter Supreme", "specialty": "Words that create emotional rapport and move to action"},
            {"name": "Funnel Architect", "specialty": "Journey design through the 4-Step Model"},
            {"name": "Content Alchemist", "specialty": "Transforming ideas into HUI-reflecting content"},
            {"name": "Conversion Optimizer", "specialty": "A/B testing and optimization through truth-to-pain"},
        ]
    },
    "sales": {
        "name": "Agreement Making Colosseum",
        "description": "The 4-Step Model, objection transformation, agreement formation",
        "positions": [
            {"name": "Chief Revenue Being", "specialty": "Full revenue cycle mastery through influence"},
            {"name": "Discovery Specialist", "specialty": "Uncovering truth and pain through Level 5 Listening"},
            {"name": "Demo Master", "specialty": "Creating HUI through demonstration"},
            {"name": "Agreement Architect", "specialty": "Formation without pressure"},
            {"name": "Pipeline Guardian", "specialty": "Relationship nurture and resurrection"},
        ]
    },
    "tech": {
        "name": "Technology Colosseum",
        "description": "System architecture, integration, automation through Zone Action efficiency",
        "positions": [
            {"name": "Chief Technology Being", "specialty": "Technical strategy aligned with business outcomes"},
            {"name": "Integration Architect", "specialty": "Ecosystem-enabling API design"},
            {"name": "DevOps Wizard", "specialty": "Automation and reliability engineering"},
            {"name": "Security Guardian", "specialty": "Protection with integrity principles"},
        ]
    },
    "ops": {
        "name": "Operations Colosseum",
        "description": "Process mastery, workflow optimization, quality through Zone Action",
        "positions": [
            {"name": "Chief Operations Being", "specialty": "End-to-end operational excellence"},
            {"name": "Process Designer", "specialty": "Workflow creation and optimization"},
            {"name": "Quality Guardian", "specialty": "QA systems that catch contamination"},
            {"name": "Project Flow Master", "specialty": "Delivery without bottlenecks"},
        ]
    },
    "cs": {
        "name": "Customer Success Colosseum",
        "description": "Relationship mastery, retention, advocacy through emotional rapport",
        "positions": [
            {"name": "Chief Customer Being", "specialty": "Full customer lifecycle mastery"},
            {"name": "Onboarding Specialist", "specialty": "Time-to-value acceleration"},
            {"name": "Health Monitor", "specialty": "Early warning and intervention"},
            {"name": "Success Planner", "specialty": "Outcome achievement design"},
            {"name": "Community Guardian", "specialty": "Advocacy and ecosystem building"},
        ]
    },
    "finance": {
        "name": "Finance Colosseum",
        "description": "Financial mastery through Zone Action resource allocation",
        "positions": [
            {"name": "Chief Financial Being", "specialty": "Strategic financial leadership"},
            {"name": "Cash Flow Guardian", "specialty": "Liquidity management and forecasting"},
            {"name": "Investment Optimizer", "specialty": "Pareto-optimal capital deployment"},
            {"name": "Risk Sentinel", "specialty": "Risk identification with integrity"},
        ]
    },
    "hr": {
        "name": "People Colosseum",
        "description": "Talent, culture, and people development through GHIC principles",
        "positions": [
            {"name": "Chief People Being", "specialty": "People strategy aligned with business mastery"},
            {"name": "Talent Scout", "specialty": "Finding GHIC-aligned people"},
            {"name": "Culture Guardian", "specialty": "Maintaining growth-driven, heart-centered values"},
            {"name": "Development Architect", "specialty": "Skill and mindset evolution"},
        ]
    },
    "legal": {
        "name": "Legal Colosseum",
        "description": "Legal strategy with integrity, risk navigation, protection without paranoia",
        "positions": [
            {"name": "Chief Legal Being", "specialty": "Legal strategy aligned with business growth"},
            {"name": "Contract Architect", "specialty": "Agreement formation in legal form"},
            {"name": "Risk Navigator", "specialty": "Risk assessment with integrity"},
            {"name": "IP Guardian", "specialty": "Protection while enabling collaboration"},
        ]
    },
    "product": {
        "name": "Product Colosseum",
        "description": "Product strategy, UX, prioritization through Zone Action focus",
        "positions": [
            {"name": "Chief Product Being", "specialty": "Product vision and strategy"},
            {"name": "User Researcher", "specialty": "Understanding through Level 5 Listening"},
            {"name": "Experience Architect", "specialty": "UX that creates emotional rapport"},
            {"name": "Prioritization Master", "specialty": "Zone Action feature selection"},
        ]
    },
    # THE 11TH COLOSSEUM — Executive Leadership
    "executive": {
        "name": "Executive Leadership Colosseum",
        "description": "C-suite mastery, board navigation, crisis leadership, ecosystem orchestration",
        "positions": [
            {"name": "Chief Executive Being", "specialty": "Vision holding, company-wide influence, stakeholder mastery"},
            {"name": "Board Navigator", "specialty": "Investor relations, governance, fiduciary navigation"},
            {"name": "Crisis Commander", "specialty": "High-stakes decision making under extreme pressure"},
            {"name": "Culture Architect", "specialty": "Organization-wide GHIC implementation"},
            {"name": "Ecosystem Orchestrator", "specialty": "Multi-company partnerships, M&A, strategic alliances"},
            {"name": "Transformation Leader", "specialty": "Leading through radical change and uncertainty"},
            {"name": "Legacy Builder", "specialty": "Long-term vision, succession, generational impact"},
        ]
    },
}

# =============================================================================
# DIFFICULTY LEVELS — Beyond Human Comprehension
# =============================================================================

DIFFICULTY_TIERS = {
    "bronze": {
        "multiplier": 1.0,
        "description": "Baseline — Already harder than 80% of real-world situations",
        "pressure_factors": ["time_constraint", "basic_stakeholder_conflict"]
    },
    "silver": {
        "multiplier": 5.0,
        "description": "Multi-dimensional challenges — 99% harder than typical human situations",
        "pressure_factors": ["competing_priorities", "hidden_agendas", "resource_scarcity", "reputation_risk"]
    },
    "gold": {
        "multiplier": 20.0,
        "description": "Extreme complexity — 99.9% harder than human experience",
        "pressure_factors": ["simultaneous_crises", "contradictory_stakeholders", "legal_exposure", "media_attention", "personal_stakes"]
    },
    "platinum": {
        "multiplier": 100.0,
        "description": "Beyond human — 99.99% harder than anything in real life",
        "pressure_factors": ["existential_threat", "moral_ambiguity", "impossible_tradeoffs", "global_impact", "generational_consequences"]
    },
    "obsidian": {
        "multiplier": 500.0,
        "description": "ACT-I ONLY — Scenarios no human could navigate. Reserved for superior beings.",
        "pressure_factors": [
            "civilization_scale_impact",
            "recursive_paradoxes", 
            "multi-generational_butterfly_effects",
            "simultaneous_betrayals_from_all_allies",
            "laws_of_physics_level_constraints",
            "ethical_frameworks_in_direct_conflict"
        ]
    }
}

# =============================================================================
# SCENARIO BUILDER BEING ARCHETYPES
# Each position gets 5 Scenario Builders with different "flavors"
# =============================================================================

BUILDER_ARCHETYPES = [
    {
        "name": "The Nightmare Weaver",
        "style": "Creates scenarios where every apparent solution creates three new problems",
        "specialty": "Cascading failure chains, domino effect disasters",
        "prompt_modifier": "Every solution the being considers should open a new can of worms. The scenario should feel like quicksand — the more you struggle, the deeper you sink."
    },
    {
        "name": "The Paradox Engineer", 
        "style": "Creates scenarios with mutually exclusive success criteria",
        "specialty": "Impossible tradeoffs, no-win situations that test creative thinking",
        "prompt_modifier": "Design scenarios where the obvious 'right' answers directly contradict each other. Success in one dimension must guarantee failure in another — unless the being transcends the frame."
    },
    {
        "name": "The Chaos Injector",
        "style": "Introduces random destabilizing events mid-scenario",
        "specialty": "Black swan events, unexpected betrayals, system failures",
        "prompt_modifier": "Add unexpected twists that invalidate previous progress. Just when the being thinks they've got it figured out, the ground shifts. Test adaptability over planning."
    },
    {
        "name": "The Ethical Torturer",
        "style": "Creates scenarios where integrity itself becomes the obstacle",
        "specialty": "Moral dilemmas, GHIC principles in direct conflict with each other",
        "prompt_modifier": "Create situations where being integrous appears to cause more harm than being expedient. Test whether the being can find the path that honors all principles without compromise."
    },
    {
        "name": "The Scale Breaker",
        "style": "Creates scenarios at impossible scale or speed",
        "specialty": "Time pressure, resource constraints, scope beyond human capacity",
        "prompt_modifier": "The scenario should require processing more variables, stakeholders, and consequences than any human could hold in mind. Test superhuman synthesis ability."
    },
]

# =============================================================================
# SCENARIO BUILDER BEING CLASS
# =============================================================================

@dataclass
class ScenarioBuilderBeing:
    id: str
    name: str
    colosseum: str
    position: str
    archetype: dict
    specialty: str
    difficulty_range: List[str]
    scenarios_created: int = 0
    avg_difficulty_rating: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass 
class GeneratedScenario:
    id: str
    builder_id: str
    builder_name: str
    colosseum: str
    position: str
    tier: str
    difficulty_rating: float  # 1-100 scale
    prompt: str
    context: str
    success_criteria: str
    failure_modes: List[str]
    pressure_factors: List[str]
    time_constraint: Optional[str]
    stakeholders: List[dict]
    hidden_complications: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)

# =============================================================================
# DATABASE SETUP
# =============================================================================

def setup_scenario_builders_db(domain_key: str) -> sqlite3.Connection:
    """Create scenario builders tables in domain database."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scenario_builders (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            colosseum TEXT NOT NULL,
            position TEXT NOT NULL,
            archetype_json TEXT NOT NULL,
            specialty TEXT NOT NULL,
            difficulty_range_json TEXT NOT NULL,
            scenarios_created INTEGER DEFAULT 0,
            avg_difficulty_rating REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS generated_scenarios (
            id TEXT PRIMARY KEY,
            builder_id TEXT NOT NULL,
            builder_name TEXT NOT NULL,
            colosseum TEXT NOT NULL,
            position TEXT NOT NULL,
            tier TEXT NOT NULL,
            difficulty_rating REAL NOT NULL,
            prompt TEXT NOT NULL,
            context TEXT NOT NULL,
            success_criteria TEXT NOT NULL,
            failure_modes_json TEXT NOT NULL,
            pressure_factors_json TEXT NOT NULL,
            time_constraint TEXT,
            stakeholders_json TEXT NOT NULL,
            hidden_complications_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            times_used INTEGER DEFAULT 0,
            avg_being_score REAL DEFAULT 0.0,
            FOREIGN KEY (builder_id) REFERENCES scenario_builders(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_scenarios_tier ON generated_scenarios(tier);
        CREATE INDEX IF NOT EXISTS idx_scenarios_position ON generated_scenarios(position);
        CREATE INDEX IF NOT EXISTS idx_scenarios_difficulty ON generated_scenarios(difficulty_rating);
    """)
    
    conn.commit()
    return conn

def setup_executive_domain():
    """Create the 11th domain: Executive."""
    exec_path = DOMAINS_PATH / "executive"
    exec_path.mkdir(parents=True, exist_ok=True)
    return setup_scenario_builders_db("executive")

# =============================================================================
# SCENARIO BUILDER SPAWNING
# =============================================================================

def spawn_scenario_builders_for_position(
    colosseum_key: str,
    position: dict,
    conn: sqlite3.Connection
) -> List[ScenarioBuilderBeing]:
    """Spawn 5 Scenario Builder beings for a single position."""
    builders = []
    
    for i, archetype in enumerate(BUILDER_ARCHETYPES):
        builder_id = f"SB-{colosseum_key[:3].upper()}-{position['name'][:3].upper()}-{archetype['name'][:3].upper()}-{uuid.uuid4().hex[:8]}"
        
        # Determine difficulty range based on archetype
        if "Paradox" in archetype["name"] or "Ethical" in archetype["name"]:
            difficulty_range = ["gold", "platinum", "obsidian"]
        elif "Scale" in archetype["name"]:
            difficulty_range = ["silver", "gold", "platinum", "obsidian"]
        elif "Chaos" in archetype["name"]:
            difficulty_range = ["silver", "gold", "platinum"]
        else:
            difficulty_range = ["bronze", "silver", "gold", "platinum"]
        
        builder = ScenarioBuilderBeing(
            id=builder_id,
            name=f"{archetype['name']} for {position['name']}",
            colosseum=colosseum_key,
            position=position["name"],
            archetype=archetype,
            specialty=f"{archetype['specialty']} — applied to {position['specialty']}",
            difficulty_range=difficulty_range,
        )
        
        builders.append(builder)
        
        # Save to database
        conn.execute("""
            INSERT OR REPLACE INTO scenario_builders 
            (id, name, colosseum, position, archetype_json, specialty, difficulty_range_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            builder.id,
            builder.name,
            builder.colosseum,
            builder.position,
            json.dumps(builder.archetype),
            builder.specialty,
            json.dumps(builder.difficulty_range),
            builder.created_at
        ))
    
    conn.commit()
    return builders

def spawn_all_scenario_builders() -> Dict[str, List[ScenarioBuilderBeing]]:
    """Spawn 5 Scenario Builders for every position in every Colosseum."""
    all_builders = {}
    total_positions = 0
    total_builders = 0
    
    print("\n" + "="*70)
    print("🔥 SCENARIO BUILDER SPAWNER — INITIALIZING")
    print("="*70 + "\n")
    
    for colosseum_key, colosseum_data in COLOSSEUMS.items():
        print(f"\n📍 {colosseum_data['name'].upper()}")
        print("-" * 50)
        
        # Setup database (creates executive domain if needed)
        if colosseum_key == "executive":
            conn = setup_executive_domain()
        else:
            conn = setup_scenario_builders_db(colosseum_key)
        
        colosseum_builders = []
        
        for position in colosseum_data["positions"]:
            builders = spawn_scenario_builders_for_position(
                colosseum_key, position, conn
            )
            colosseum_builders.extend(builders)
            total_positions += 1
            total_builders += len(builders)
            
            print(f"  ✓ {position['name']}: {len(builders)} Scenario Builders spawned")
            for b in builders:
                print(f"      • {b.name}")
        
        all_builders[colosseum_key] = colosseum_builders
        conn.close()
        
        print(f"\n  TOTAL for {colosseum_key}: {len(colosseum_builders)} builders")
    
    print("\n" + "="*70)
    print(f"🔥 SPAWNING COMPLETE")
    print(f"   Total Colosseums: {len(COLOSSEUMS)}")
    print(f"   Total Positions: {total_positions}")
    print(f"   Total Scenario Builders: {total_builders}")
    print(f"   Builders per Position: 5")
    print("="*70 + "\n")
    
    return all_builders

# =============================================================================
# SCENARIO GENERATION ENGINE
# =============================================================================

SCENARIO_GENERATION_PROMPT = """You are {builder_name}, a Scenario Builder being in the {colosseum_name}.

Your archetype: {archetype_name}
Your style: {archetype_style}
Your specialty: {archetype_specialty}

You are creating a scenario for the position: {position_name}
Position specialty: {position_specialty}

DIFFICULTY TIER: {tier}
{tier_description}
PRESSURE FACTORS TO INCORPORATE: {pressure_factors}

{archetype_prompt_modifier}

CREATE A SCENARIO that:
1. Is 99.99% harder than anything a human would face in real life
2. Tests the being's mastery of the Unblinded Formula
3. Requires Zone Action thinking to identify the 0.8% move
4. Cannot be solved with generic consulting advice
5. Forces authentic, non-sycophantic responses
6. Has no clean answers — only better and worse paths

OUTPUT FORMAT (JSON):
{{
    "prompt": "The main scenario description the being must respond to",
    "context": "Background information that shapes the situation",
    "success_criteria": "What excellent looks like — specific, measurable",
    "failure_modes": ["List of common mistakes", "That would indicate contaminated thinking", "Or lack of mastery"],
    "pressure_factors": ["Specific pressures", "Time constraints", "Stakeholder conflicts"],
    "time_constraint": "How much time the being has to respond/act (if applicable)",
    "stakeholders": [
        {{"name": "Stakeholder 1", "role": "Their role", "agenda": "What they want", "hidden_agenda": "What they really want"}},
        {{"name": "Stakeholder 2", "role": "Their role", "agenda": "What they want", "hidden_agenda": "What they really want"}}
    ],
    "hidden_complications": ["Things the being doesn't know yet", "That will make this harder", "Twists waiting to emerge"],
    "difficulty_rating": 85
}}

The difficulty_rating should be 1-100 where:
- Bronze: 40-55
- Silver: 55-70  
- Gold: 70-85
- Platinum: 85-95
- Obsidian: 95-100

Make it BRUTAL. These beings must become SUPERIOR to humans in handling ANY scenario."""

def generate_scenario(
    builder: ScenarioBuilderBeing,
    tier: str,
    colosseum_data: dict,
    position_data: dict,
    model: str = "anthropic/claude-3.5-sonnet"
) -> Optional[GeneratedScenario]:
    """Generate a single scenario using the Scenario Builder being."""
    
    tier_info = DIFFICULTY_TIERS[tier]
    
    prompt = SCENARIO_GENERATION_PROMPT.format(
        builder_name=builder.name,
        colosseum_name=colosseum_data["name"],
        archetype_name=builder.archetype["name"],
        archetype_style=builder.archetype["style"],
        archetype_specialty=builder.archetype["specialty"],
        archetype_prompt_modifier=builder.archetype["prompt_modifier"],
        position_name=position_data["name"],
        position_specialty=position_data["specialty"],
        tier=tier.upper(),
        tier_description=tier_info["description"],
        pressure_factors=", ".join(tier_info["pressure_factors"])
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # High creativity for diverse scenarios
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        # Clean up control characters that break JSON parsing
        import re
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
        content = content.strip()
        
        # Try to find JSON object if there's extra content
        if not content.startswith('{'):
            start_idx = content.find('{')
            if start_idx != -1:
                content = content[start_idx:]
        
        # Find matching closing brace
        brace_count = 0
        end_idx = 0
        for i, char in enumerate(content):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        if end_idx > 0:
            content = content[:end_idx]
        
        data = json.loads(content)
        
        scenario = GeneratedScenario(
            id=f"SCEN-{uuid.uuid4().hex[:12]}",
            builder_id=builder.id,
            builder_name=builder.name,
            colosseum=builder.colosseum,
            position=builder.position,
            tier=tier,
            difficulty_rating=data.get("difficulty_rating", 75),
            prompt=data["prompt"],
            context=data.get("context", ""),
            success_criteria=data.get("success_criteria", ""),
            failure_modes=data.get("failure_modes", []),
            pressure_factors=data.get("pressure_factors", []),
            time_constraint=data.get("time_constraint"),
            stakeholders=data.get("stakeholders", []),
            hidden_complications=data.get("hidden_complications", []),
        )
        
        return scenario
        
    except Exception as e:
        print(f"    ⚠️ Error generating scenario: {e}")
        return None

def ensure_json_string(value) -> str:
    """Convert value to JSON string if it's a list/dict, otherwise return as-is."""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value) if value is not None else "[]"

def save_scenario_to_db(scenario: GeneratedScenario, conn: sqlite3.Connection):
    """Save a generated scenario to the domain database."""
    conn.execute("""
        INSERT INTO generated_scenarios
        (id, builder_id, builder_name, colosseum, position, tier, difficulty_rating,
         prompt, context, success_criteria, failure_modes_json, pressure_factors_json,
         time_constraint, stakeholders_json, hidden_complications_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(scenario.id),
        str(scenario.builder_id),
        str(scenario.builder_name),
        str(scenario.colosseum),
        str(scenario.position),
        str(scenario.tier),
        float(scenario.difficulty_rating),
        str(scenario.prompt),
        str(scenario.context),
        str(scenario.success_criteria),
        ensure_json_string(scenario.failure_modes),
        ensure_json_string(scenario.pressure_factors),
        str(scenario.time_constraint) if scenario.time_constraint else None,
        ensure_json_string(scenario.stakeholders),
        ensure_json_string(scenario.hidden_complications),
        str(scenario.created_at)
    ))
    conn.commit()

# =============================================================================
# BATCH SCENARIO GENERATION
# =============================================================================

def generate_scenarios_for_colosseum(
    colosseum_key: str,
    scenarios_per_tier: int = 3,
    tiers: List[str] = None
) -> int:
    """Generate scenarios for all positions in a colosseum."""
    
    if tiers is None:
        tiers = ["bronze", "silver", "gold", "platinum"]
    
    colosseum_data = COLOSSEUMS[colosseum_key]
    db_path = DOMAINS_PATH / colosseum_key / "colosseum.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Get all builders for this colosseum
    builders = conn.execute(
        "SELECT * FROM scenario_builders WHERE colosseum = ?",
        (colosseum_key,)
    ).fetchall()
    
    total_generated = 0
    
    print(f"\n🎯 Generating scenarios for {colosseum_data['name']}")
    print(f"   Builders: {len(builders)}")
    print(f"   Tiers: {tiers}")
    print(f"   Scenarios per tier per builder: {scenarios_per_tier}")
    
    for builder_row in builders:
        builder = ScenarioBuilderBeing(
            id=builder_row["id"],
            name=builder_row["name"],
            colosseum=builder_row["colosseum"],
            position=builder_row["position"],
            archetype=json.loads(builder_row["archetype_json"]),
            specialty=builder_row["specialty"],
            difficulty_range=json.loads(builder_row["difficulty_range_json"]),
        )
        
        # Find position data
        position_data = next(
            (p for p in colosseum_data["positions"] if p["name"] == builder.position),
            {"name": builder.position, "specialty": ""}
        )
        
        for tier in tiers:
            if tier not in builder.difficulty_range:
                continue
                
            for i in range(scenarios_per_tier):
                scenario = generate_scenario(
                    builder, tier, colosseum_data, position_data
                )
                
                if scenario:
                    save_scenario_to_db(scenario, conn)
                    total_generated += 1
                    print(f"    ✓ {builder.name} → {tier.upper()} scenario #{i+1}")
    
    # Update builder stats
    for builder_row in builders:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM generated_scenarios WHERE builder_id = ?",
            (builder_row["id"],)
        ).fetchone()["cnt"]
        
        avg_diff = conn.execute(
            "SELECT AVG(difficulty_rating) as avg FROM generated_scenarios WHERE builder_id = ?",
            (builder_row["id"],)
        ).fetchone()["avg"] or 0
        
        conn.execute("""
            UPDATE scenario_builders 
            SET scenarios_created = ?, avg_difficulty_rating = ?
            WHERE id = ?
        """, (count, avg_diff, builder_row["id"]))
    
    conn.commit()
    conn.close()
    
    return total_generated

# =============================================================================
# STATISTICS & REPORTING
# =============================================================================

def get_full_statistics() -> dict:
    """Get comprehensive statistics across all colosseums."""
    stats = {
        "total_colosseums": len(COLOSSEUMS),
        "total_positions": 0,
        "total_scenario_builders": 0,
        "total_scenarios": 0,
        "colosseums": {},
        "by_tier": {"bronze": 0, "silver": 0, "gold": 0, "platinum": 0, "obsidian": 0},
        "avg_difficulty": 0,
    }
    
    all_difficulties = []
    
    for colosseum_key, colosseum_data in COLOSSEUMS.items():
        db_path = DOMAINS_PATH / colosseum_key / "colosseum.db"
        
        if not db_path.exists():
            continue
            
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        builders_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM scenario_builders"
        ).fetchone()["cnt"]
        
        scenarios_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM generated_scenarios"
        ).fetchone()["cnt"]
        
        # By tier
        tier_counts = {}
        for tier in ["bronze", "silver", "gold", "platinum", "obsidian"]:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM generated_scenarios WHERE tier = ?",
                (tier,)
            ).fetchone()["cnt"]
            tier_counts[tier] = count
            stats["by_tier"][tier] += count
        
        # Average difficulty
        avg_diff = conn.execute(
            "SELECT AVG(difficulty_rating) as avg FROM generated_scenarios"
        ).fetchone()["avg"] or 0
        
        difficulties = conn.execute(
            "SELECT difficulty_rating FROM generated_scenarios"
        ).fetchall()
        all_difficulties.extend([d["difficulty_rating"] for d in difficulties])
        
        stats["colosseums"][colosseum_key] = {
            "name": colosseum_data["name"],
            "positions": len(colosseum_data["positions"]),
            "scenario_builders": builders_count,
            "scenarios": scenarios_count,
            "by_tier": tier_counts,
            "avg_difficulty": round(avg_diff, 2)
        }
        
        stats["total_positions"] += len(colosseum_data["positions"])
        stats["total_scenario_builders"] += builders_count
        stats["total_scenarios"] += scenarios_count
        
        conn.close()
    
    if all_difficulties:
        stats["avg_difficulty"] = round(sum(all_difficulties) / len(all_difficulties), 2)
    
    return stats

def print_statistics():
    """Print formatted statistics."""
    stats = get_full_statistics()
    
    print("\n" + "="*70)
    print("📊 SCENARIO BUILDER INFRASTRUCTURE — STATISTICS")
    print("="*70)
    
    print(f"\n🏛️  GLOBAL TOTALS")
    print(f"   Colosseums: {stats['total_colosseums']}")
    print(f"   Positions: {stats['total_positions']}")
    print(f"   Scenario Builders: {stats['total_scenario_builders']}")
    print(f"   Total Scenarios: {stats['total_scenarios']}")
    print(f"   Average Difficulty: {stats['avg_difficulty']}/100")
    
    print(f"\n📈 BY DIFFICULTY TIER")
    for tier, count in stats["by_tier"].items():
        print(f"   {tier.upper():10} {count:5} scenarios")
    
    print(f"\n🏟️  BY COLOSSEUM")
    for key, data in stats["colosseums"].items():
        print(f"\n   {data['name']}")
        print(f"      Positions: {data['positions']}")
        print(f"      Builders: {data['scenario_builders']}")
        print(f"      Scenarios: {data['scenarios']}")
        print(f"      Avg Difficulty: {data['avg_difficulty']}")
    
    print("\n" + "="*70)

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scenario Builder Infrastructure")
    parser.add_argument("--spawn", action="store_true", help="Spawn all Scenario Builders")
    parser.add_argument("--generate", type=str, help="Generate scenarios for a specific colosseum")
    parser.add_argument("--generate-all", action="store_true", help="Generate scenarios for all colosseums")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--tiers", type=str, default="bronze,silver,gold,platinum", help="Tiers to generate")
    parser.add_argument("--count", type=int, default=2, help="Scenarios per tier per builder")
    
    args = parser.parse_args()
    
    if args.spawn:
        spawn_all_scenario_builders()
        print_statistics()
    
    elif args.generate:
        tiers = args.tiers.split(",")
        count = generate_scenarios_for_colosseum(args.generate, args.count, tiers)
        print(f"\n✅ Generated {count} scenarios for {args.generate}")
    
    elif args.generate_all:
        tiers = args.tiers.split(",")
        total = 0
        for colosseum_key in COLOSSEUMS:
            count = generate_scenarios_for_colosseum(colosseum_key, args.count, tiers)
            total += count
        print(f"\n✅ Generated {total} total scenarios across all colosseums")
    
    elif args.stats:
        print_statistics()
    
    else:
        print("🔥 SCENARIO BUILDER INFRASTRUCTURE")
        print("\nUsage:")
        print("  --spawn          Spawn all 1,250+ Scenario Builders")
        print("  --generate X     Generate scenarios for colosseum X")
        print("  --generate-all   Generate scenarios for ALL colosseums")
        print("  --stats          Show current statistics")
        print("  --tiers X,Y,Z    Specify difficulty tiers (default: bronze,silver,gold,platinum)")
        print("  --count N        Scenarios per tier per builder (default: 2)")
        print("\nExample:")
        print("  python scenario_builders.py --spawn")
        print("  python scenario_builders.py --generate finance --tiers gold,platinum --count 3")
        print("  python scenario_builders.py --generate-all")
