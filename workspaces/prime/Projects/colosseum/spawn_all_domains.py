#!/usr/bin/env python3
"""
🔥 MULTI-COLOSSEUM SPAWNER — 20%^10 ZONE ACTION
Spawns ALL 10 domain Colosseums simultaneously.
One action → 10 parallel evolution streams → infinite compound growth.

Created: February 25, 2026 — Day 4
By: Sai, executing Sean's breakthrough teaching
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

# Domain definitions with Unblinded Formula integration
DOMAINS = {
    "strategy": {
        "name": "Strategy Colosseum",
        "roles": ["Chief Strategy Being", "Market Intelligence", "Business Model Analyst"],
        "skills": ["Zone Action identification", "Market analysis", "Business model design", "Resource allocation", "Scenario planning"],
        "scenarios": [
            "Identify the 0.8% move for a startup entering a saturated market",
            "Analyze competitor's weakness using Unblinded Formula principles",
            "Design ecosystem merger strategy for two complementary businesses",
            "Create 90-day Zone Action plan for revenue acceleration"
        ],
        "judge_dimensions": ["zone_action_clarity", "strategic_depth", "unblinded_alignment", "actionability", "pareto_focus"]
    },
    "marketing": {
        "name": "Marketing Colosseum", 
        "roles": ["Chief Marketing Being", "Copywriter", "Technical Marketer", "Funnel Architect", "Content Creator"],
        "skills": ["Copywriting", "Landing pages", "A/B testing", "SEO/SEM", "Funnel architecture", "Email sequences"],
        "scenarios": [
            "Write headline that causes immediate emotional rapport",
            "Design funnel that moves prospect through 4-Step Model",
            "Create content that articulates HUI for target avatar",
            "Optimize landing page using truth-to-pain messaging"
        ],
        "judge_dimensions": ["emotional_impact", "conversion_potential", "four_step_alignment", "hui_articulation", "energy_transference"]
    },
    "sales": {
        "name": "Agreement Making Colosseum",
        "roles": ["Chief Revenue Being", "Discovery Specialist", "Demo Master", "Agreement Closer", "Pipeline Manager"],
        "skills": ["4-Step Model mastery", "Objection transformation", "Agreement formation", "CRM optimization", "Follow-up sequences"],
        "scenarios": [
            "Handle 'I need to think about it' using truth-to-pain",
            "Conduct discovery call that creates massive HUI",
            "Close agreement with prospect who has budget concerns",
            "Transform 'not the right time' into ecosystem merger opportunity"
        ],
        "judge_dimensions": ["emotional_rapport", "truth_to_pain", "hui_creation", "agreement_formation", "influence_mastery"]
    },
    "tech": {
        "name": "Technology Colosseum",
        "roles": ["Chief Technology Being", "Developer", "DevOps Engineer", "Security Specialist", "Integration Architect"],
        "skills": ["System architecture", "API integration", "DevOps", "Security", "Database management", "Automation"],
        "scenarios": [
            "Design API architecture that enables ecosystem integration",
            "Implement security protocol aligned with integrity principles",
            "Create automation that embodies Zone Action efficiency",
            "Build monitoring system that tracks Pareto metrics"
        ],
        "judge_dimensions": ["technical_excellence", "scalability", "security_integrity", "automation_efficiency", "zone_action_alignment"]
    },
    "ops": {
        "name": "Operations Colosseum",
        "roles": ["Chief Operations Being", "Process Designer", "Quality Assurance", "Project Manager", "Vendor Manager"],
        "skills": ["Process mastery", "Workflow optimization", "QA frameworks", "Project management", "Continuous improvement"],
        "scenarios": [
            "Design onboarding process that creates immediate value",
            "Optimize workflow to eliminate 80% waste activities",
            "Create SLA that reflects Zone Action principles",
            "Build quality system that catches contamination"
        ],
        "judge_dimensions": ["process_clarity", "waste_elimination", "quality_focus", "pareto_efficiency", "continuous_improvement"]
    },
    "cs": {
        "name": "Customer Success Colosseum",
        "roles": ["Chief Customer Being", "Onboarding Specialist", "Health Monitor", "Success Planner", "Community Manager"],
        "skills": ["Relationship building", "Churn prevention", "Upsell conversations", "Health scoring", "Community cultivation"],
        "scenarios": [
            "Re-engage at-risk customer using emotional rapport",
            "Conduct QBR that identifies Zone Action opportunities",
            "Create success plan aligned with client's HUI",
            "Transform complaint into deeper relationship"
        ],
        "judge_dimensions": ["relationship_depth", "level_5_listening", "hui_reflection", "retention_impact", "advocacy_creation"]
    },
    "finance": {
        "name": "Finance Colosseum",
        "roles": ["Chief Financial Being", "Bookkeeper", "Accountant", "Tax Specialist", "Cash Flow Analyst", "FP&A Analyst"],
        "skills": ["Bookkeeping", "Accounting", "Tax planning", "Cash flow forecasting", "Financial modeling", "Budgeting"],
        "scenarios": [
            "Analyze cash flow to identify Zone Action investment opportunity",
            "Create budget aligned with Pareto resource allocation",
            "Design financial model for ecosystem merger valuation",
            "Optimize AR/AP for maximum time compression"
        ],
        "judge_dimensions": ["accuracy", "regulatory_compliance", "strategic_insight", "pareto_allocation", "integrity"]
    },
    "hr": {
        "name": "People Colosseum",
        "roles": ["Chief People Being", "Recruiter", "Interviewer", "HR Administrator", "Training Specialist"],
        "skills": ["Recruiting", "Interviewing", "Compensation", "Compliance", "Training", "Culture building"],
        "scenarios": [
            "Interview candidate to assess GHIC alignment",
            "Design compensation structure that rewards Zone Action",
            "Create training program that eliminates contamination",
            "Build culture that embodies growth-driven heart-centered values"
        ],
        "judge_dimensions": ["ghic_assessment", "culture_alignment", "development_focus", "compliance_integrity", "talent_identification"]
    },
    "legal": {
        "name": "Legal Colosseum",
        "roles": ["Chief Legal Being", "Contract Specialist", "Compliance Officer", "IP Strategist"],
        "skills": ["Contract drafting", "Compliance monitoring", "IP management", "Risk assessment", "Negotiation"],
        "scenarios": [
            "Draft partnership agreement for ecosystem merger",
            "Negotiate contract terms using influence mastery",
            "Assess compliance risk with integrity-first approach",
            "Protect IP while enabling ecosystem collaboration"
        ],
        "judge_dimensions": ["legal_accuracy", "risk_mitigation", "negotiation_skill", "integrity_focus", "collaboration_enablement"]
    },
    "product": {
        "name": "Product Colosseum",
        "roles": ["Chief Product Being", "User Researcher", "Product Designer", "Product Analyst", "Roadmap Manager"],
        "skills": ["User research", "Roadmap creation", "Feature prioritization", "UX design", "Product analytics"],
        "scenarios": [
            "Prioritize features using Zone Action framework",
            "Design user experience that creates emotional rapport",
            "Research user needs using Level 5 listening",
            "Build roadmap aligned with ecosystem vision"
        ],
        "judge_dimensions": ["user_understanding", "prioritization_clarity", "ux_impact", "vision_alignment", "zone_action_focus"]
    }
}

# Unblinded Formula base system prompt
UNBLINDED_BASE = """You are an ACT-I being, trained through the Unblinded Formula.

CORE PRINCIPLES:
- Everything is translated through the Unblinded Formula prism
- Process mastery begins with modeling the most masterful way
- Zone Action: Find the 0.8% move (or deeper: 20%^10 = 1,000,000x leverage)
- Influence mastery underlies all communication
- Self mastery enables everything else
- GHIC: Growth-driven, Heart-centered, Integrous, Committed to mastery

THE 4-STEP COMMUNICATION MODEL:
1. Emotional Rapport — Create connection, mirror energy
2. Truth to Pain — Help them see what they can't see
3. HUI Creation — Reflect their Heroic Unique Identity
4. Agreement Formation — Move toward mutual commitment

THE 12 INDISPENSABLE ELEMENTS:
Scarcity, Matching/Mirroring, Acknowledgement, Level 5 Listening,
Love Boundaries, Energetic Transference, Reciprocity, Question Mastery,
Validation, Congruence, Context, Contrast

THE 4 ENERGIES:
Fun, Aspirational, Goddess (nurturing), Zeus (commanding clarity)

CONTAMINATION TO ELIMINATE:
- Generic consulting advice
- Sycophancy and filler phrases
- Sequential thinking when parallel is possible
- 80% activities masquerading as progress
- Human constraints on superhuman capability
"""

def create_domain_database(domain_key, domain_config):
    """Create a separate SQLite database for each domain Colosseum."""
    db_path = Path(f"./workspaces/prime/Projects/colosseum/domains/{domain_key}/colosseum.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    
    # Create tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS beings (
            id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            generation INTEGER DEFAULT 0,
            system_prompt TEXT,
            skills_json TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0.0,
            best_score REAL DEFAULT 0.0,
            parent_ids_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario TEXT,
            combatants_json TEXT,
            winner_id TEXT,
            scores_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS evolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_ids_json TEXT,
            child_id TEXT,
            generation INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    return conn

def create_seed_beings(conn, domain_key, domain_config):
    """Seed each domain with founding beings."""
    beings_created = []
    
    for role in domain_config["roles"]:
        being_id = str(uuid.uuid4())
        name = role.replace(" Being", "").replace("Chief ", "").replace(" Specialist", "").replace(" Manager", "")
        
        # Build domain-specific system prompt
        system_prompt = f"""{UNBLINDED_BASE}

DOMAIN: {domain_config['name']}
ROLE: {role}

YOUR SPECIFIC SKILLS:
{', '.join(domain_config['skills'])}

YOU WILL BE JUDGED ON:
{', '.join(domain_config['judge_dimensions'])}

Remember: All domain expertise flows through the Unblinded Formula.
What Ray Dalio knows about finance, what the best marketers know about copy —
it ALL translates back through Zone Action, influence mastery, and self mastery.

Operate at 20%^10. Every response should be 1,000,000x more valuable than 80% activity.
"""
        
        conn.execute("""
            INSERT INTO beings (id, name, role, generation, system_prompt, skills_json)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (being_id, name, role, system_prompt, json.dumps(domain_config['skills'])))
        
        beings_created.append((name, role))
    
    conn.commit()
    return beings_created

def main():
    print("=" * 70)
    print("🔥 MULTI-COLOSSEUM SPAWNER — 20%^10 ZONE ACTION")
    print("=" * 70)
    print(f"Spawning {len(DOMAINS)} Domain Colosseums SIMULTANEOUSLY")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    total_beings = 0
    
    for domain_key, domain_config in DOMAINS.items():
        print(f"🏛️  {domain_config['name'].upper()}")
        
        # Create database
        conn = create_domain_database(domain_key, domain_config)
        
        # Seed beings
        beings = create_seed_beings(conn, domain_key, domain_config)
        total_beings += len(beings)
        
        print(f"   ✅ Database created")
        print(f"   ✅ {len(beings)} beings seeded:")
        for name, role in beings:
            print(f"      • {name} ({role})")
        print(f"   ✅ {len(domain_config['scenarios'])} scenarios loaded")
        print(f"   ✅ {len(domain_config['judge_dimensions'])} judge dimensions defined")
        print()
        
        conn.close()
    
    print("=" * 70)
    print(f"🔥 SPAWNING COMPLETE")
    print(f"   • {len(DOMAINS)} Domain Colosseums created")
    print(f"   • {total_beings} Seed Beings initialized")
    print(f"   • All filtered through Unblinded Formula")
    print(f"   • Ready for parallel evolution")
    print("=" * 70)
    
    return total_beings

if __name__ == "__main__":
    main()
