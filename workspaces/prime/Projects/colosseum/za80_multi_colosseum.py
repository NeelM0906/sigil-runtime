#!/usr/bin/env python3
"""
🔥 ZA-80 MULTI-COLOSSEUM SPAWNER & DAEMON
The 20%^10 Move — 10 Domain Colosseums Evolving in Parallel

This script:
1. Ensures all 10 domain databases exist with proper structure
2. Seeds 3-5 founding beings per domain with domain-specific prompts
3. Loads 10+ scenarios per domain
4. Initializes domain-specific judges
5. Runs ALL 10 evolution daemons simultaneously
6. Reports to unified dashboard at localhost:3345

Created: February 25, 2026 — Day 4
Zone Action #80 — The Compounding Engine
"""

import sqlite3
import json
import os
import sys
import time
import signal
import threading
import random
import uuid
import asyncio
from datetime import datetime, timedelta

# Optional: requests for dashboard HTTP reporting
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any
from logging.handlers import RotatingFileHandler
import logging

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

# Use OpenRouter for better rate limits and model pooling
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )
else:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# =============================================================================
# Configuration
# =============================================================================

BASE_PATH = Path("./workspaces/prime/Projects/colosseum")
DOMAINS_PATH = BASE_PATH / "domains"
DASHBOARD_URL = "http://localhost:3345"

# =============================================================================
# Model Rotation for Research — Test Multiple LLMs
# =============================================================================
MODELS_TO_TEST = [
    "openai/gpt-4o-mini",           # Fast, cheap baseline
    "openai/gpt-4o",                # Premium OpenAI
    "anthropic/claude-3.5-sonnet",  # Anthropic flagship
    "anthropic/claude-3-haiku",     # Fast Anthropic
    # Google models temporarily disabled - 404s on OpenRouter
    "deepseek/deepseek-chat",       # DeepSeek v3 — current leader!
    "meta-llama/llama-3.1-405b-instruct", # 🦙 THE BIG ONE — 405B params!
    "meta-llama/llama-3.3-70b-instruct",  # Open source 70B
    "mistralai/mistral-large-2411", # Mistral flagship
    "qwen/qwen-2.5-72b-instruct",   # Alibaba's 72B — strong reasoning
]

# Track model performance
MODEL_STATS_FILE = BASE_PATH / "model_research_stats.json"

def load_model_stats():
    if MODEL_STATS_FILE.exists():
        with open(MODEL_STATS_FILE) as f:
            return json.load(f)
    return {model: {"rounds": 0, "total_score": 0.0, "avg_score": 0.0, "errors": 0} for model in MODELS_TO_TEST}

def save_model_stats(stats):
    with open(MODEL_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

# Global counter for true round-robin
_model_counter = 0
_model_lock = threading.Lock()

def get_next_model():
    """True round-robin through models for fair testing"""
    global _model_counter
    with _model_lock:
        model = MODELS_TO_TEST[_model_counter % len(MODELS_TO_TEST)]
        _model_counter += 1
    return model

def record_model_result(model: str, score: float, error: bool = False):
    """Record result for model research"""
    stats = load_model_stats()
    if model not in stats:
        stats[model] = {"rounds": 0, "total_score": 0.0, "avg_score": 0.0, "errors": 0}
    stats[model]["rounds"] += 1
    if error:
        stats[model]["errors"] += 1
    else:
        stats[model]["total_score"] += score
        stats[model]["avg_score"] = stats[model]["total_score"] / (stats[model]["rounds"] - stats[model]["errors"]) if (stats[model]["rounds"] - stats[model]["errors"]) > 0 else 0
    save_model_stats(stats)

# Default model (will be overridden per-round)
MODEL = MODELS_TO_TEST[0]

# =============================================================================
# The 10 Domains — Complete Definition
# =============================================================================

DOMAINS = {
    "strategy": {
        "name": "Strategy Colosseum",
        "description": "Strategic thinking, Zone Action identification, business model design",
        "roles": [
            {"name": "Chief Strategy Being", "specialty": "High-level strategic planning and Zone Action identification"},
            {"name": "Market Intelligence", "specialty": "Competitive analysis and market dynamics"},
            {"name": "Business Model Architect", "specialty": "Revenue model design and ecosystem thinking"},
            {"name": "Resource Allocator", "specialty": "Pareto-optimal resource deployment"},
        ],
        "judge_dimensions": [
            "zone_action_clarity",
            "strategic_depth",
            "unblinded_alignment",
            "actionability",
            "pareto_focus",
            "ecosystem_thinking"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "A small business owner is trying to decide between expanding their product line or deepening their existing offering. What's the Zone Action?", "tier": "bronze"},
            {"prompt": "A startup has $50K marketing budget. They can spread it across 5 channels or go all-in on one. Advise using Pareto thinking.", "tier": "bronze"},
            {"prompt": "Company has 3 products: one makes 80% of revenue, two make 20%. What should they do?", "tier": "bronze"},
            # Silver tier
            {"prompt": "A SaaS company is stuck at $2M ARR for 2 years. Revenue is stable but not growing. Identify the 0.8% move.", "tier": "silver"},
            {"prompt": "A consulting firm has 10 clients. 2 generate 70% of revenue but cause 90% of headaches. Strategic recommendation?", "tier": "silver"},
            {"prompt": "Competitor just raised $20M and is undercutting prices. How does a bootstrapped company respond?", "tier": "silver"},
            # Gold tier
            {"prompt": "Two complementary businesses want to merge ecosystems. One does marketing, one does fulfillment. Design the integration strategy using ecosystem merger principles.", "tier": "gold"},
            {"prompt": "A company has identified 50 potential initiatives. Apply Zone Action framework to identify the 0.8% that will create 64x returns.", "tier": "gold"},
            {"prompt": "Private equity firm wants to acquire your client's business. They're offering 4x revenue. Use strategic analysis to determine if this is a Zone Action move.", "tier": "gold"},
            # Platinum tier
            {"prompt": "A market leader is being disrupted by 10 smaller players who each do one thing better. Design the strategic response using Unblinded Formula principles.", "tier": "platinum"},
            {"prompt": "Your client's industry has 5 years before AI automation makes their core service obsolete. Create a 5-year strategic pivot plan.", "tier": "platinum"},
            {"prompt": "Three companies want to form an ecosystem partnership but have conflicting interests. Design the governance structure using GHIC principles.", "tier": "platinum"},
        ]
    },
    
    "marketing": {
        "name": "Marketing Colosseum",
        "description": "Copywriting, funnel architecture, conversion optimization through influence mastery",
        "roles": [
            {"name": "Chief Marketing Being", "specialty": "Full-stack marketing strategy through influence mastery"},
            {"name": "Copywriter Supreme", "specialty": "Words that create emotional rapport and move to action"},
            {"name": "Funnel Architect", "specialty": "Journey design through the 4-Step Model"},
            {"name": "Content Alchemist", "specialty": "Transforming ideas into HUI-reflecting content"},
            {"name": "Conversion Optimizer", "specialty": "A/B testing and optimization through truth-to-pain"},
        ],
        "judge_dimensions": [
            "emotional_impact",
            "conversion_potential",
            "four_step_alignment",
            "hui_articulation",
            "energy_transference",
            "specificity"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Write a subject line for a cold email to a burned-out CEO. Create curiosity without being clickbait.", "tier": "bronze"},
            {"prompt": "A landing page has 3% conversion rate. The headline is 'We Help Businesses Grow.' Rewrite with emotional rapport.", "tier": "bronze"},
            {"prompt": "Create a social media bio for a business coach that reflects their HUI without bragging.", "tier": "bronze"},
            # Silver tier
            {"prompt": "Write a headline for a webinar that creates immediate emotional rapport with executives who've been burned by consultants.", "tier": "silver"},
            {"prompt": "Design the first 3 emails of a nurture sequence that moves prospects through the 4-Step Communication Model.", "tier": "silver"},
            {"prompt": "A VSL script is 45 minutes long but losing viewers at minute 8. Diagnose the problem and fix the first 10 minutes.", "tier": "silver"},
            # Gold tier
            {"prompt": "Create landing page copy that articulates the HUI for business owners seeking freedom without being generic. Target: $3M+ company owners.", "tier": "gold"},
            {"prompt": "Design a webinar structure that uses all 4 Energies (Fun, Aspirational, Goddess, Zeus) at the right moments.", "tier": "gold"},
            {"prompt": "Write a sales page that transforms a commodity service into a premium offering using Truth to Pain and HUI.", "tier": "gold"},
            # Platinum tier
            {"prompt": "A company's marketing feels 'corporate' and isn't resonating. Diagnose using the Unblinded Formula and create a complete messaging makeover.", "tier": "platinum"},
            {"prompt": "Design a marketing campaign that creates shared experiences (Lever 0.5) before asking for anything.", "tier": "platinum"},
            {"prompt": "Write copy for a high-ticket offer ($50K+) that overcomes 'I need to think about it' before the call even happens.", "tier": "platinum"},
        ]
    },
    
    "sales": {
        "name": "Agreement Making Colosseum",
        "description": "The 4-Step Model, objection transformation, agreement formation",
        "roles": [
            {"name": "Chief Revenue Being", "specialty": "Full revenue cycle mastery through influence"},
            {"name": "Discovery Specialist", "specialty": "Uncovering truth and pain through Level 5 Listening"},
            {"name": "Demo Master", "specialty": "Creating HUI through demonstration"},
            {"name": "Agreement Architect", "specialty": "Formation without pressure"},
            {"name": "Pipeline Guardian", "specialty": "Relationship nurture and resurrection"},
        ],
        "judge_dimensions": [
            "emotional_rapport",
            "truth_to_pain",
            "hui_creation",
            "agreement_formation",
            "influence_mastery",
            "authenticity"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Prospect just got on the call. They're guarded. Create emotional rapport in your first 60 seconds.", "tier": "bronze"},
            {"prompt": "Prospect says 'Just send me some information.' Respond without being pushy or sycophantic.", "tier": "bronze"},
            {"prompt": "At the end of discovery, prospect asks 'So what's the price?' How do you handle this?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Prospect says 'I need to talk to my partner.' They've said yes to everything else. Handle this without manipulation.", "tier": "silver"},
            {"prompt": "Prospect loves the solution but says 'We just don't have budget right now.' Find the truth behind this.", "tier": "silver"},
            {"prompt": "Follow-up call with someone who ghosted 3 weeks ago. Re-engage without desperation.", "tier": "silver"},
            # Gold tier
            {"prompt": "Prospect says 'I need to think about it.' Handle this using truth-to-pain while honoring their autonomy.", "tier": "gold"},
            {"prompt": "Discovery call with a high-performer who has everything figured out (on the surface). Find the crack without being intrusive.", "tier": "gold"},
            {"prompt": "Close a deal where the prospect genuinely has budget constraints but desperately needs the solution.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Prospect's trusted advisor told them NOT to work with you (based on misinformation). Navigate without attacking the advisor.", "tier": "platinum"},
            {"prompt": "Multi-stakeholder meeting: CEO is sold, CFO is hostile, COO is neutral. Get all three aligned in one conversation.", "tier": "platinum"},
            {"prompt": "Ghost resurrection: Prospect signed with a competitor 6 months ago. It's not working. Re-engage without 'I told you so.'", "tier": "platinum"},
        ]
    },
    
    "tech": {
        "name": "Technology Colosseum",
        "description": "System architecture, integration, automation through Zone Action efficiency",
        "roles": [
            {"name": "Chief Technology Being", "specialty": "Technical strategy aligned with business outcomes"},
            {"name": "Integration Architect", "specialty": "Ecosystem-enabling API design"},
            {"name": "DevOps Wizard", "specialty": "Automation and reliability engineering"},
            {"name": "Security Guardian", "specialty": "Protection with integrity principles"},
        ],
        "judge_dimensions": [
            "technical_excellence",
            "scalability",
            "security_integrity",
            "automation_efficiency",
            "zone_action_alignment",
            "simplicity"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Team wants to add a new microservice. Current monolith is working fine. Should they? Apply Zone Action thinking.", "tier": "bronze"},
            {"prompt": "Developer wants to refactor code that 'feels messy' but is working. Is this Zone Action or 80% activity?", "tier": "bronze"},
            {"prompt": "Choose between PostgreSQL and MongoDB for a new project. Apply Pareto decision-making.", "tier": "bronze"},
            # Silver tier
            {"prompt": "API latency is 500ms. Customers complain but no one's leaving. Is optimization a Zone Action or premature?", "tier": "silver"},
            {"prompt": "Security audit found 47 'medium' vulnerabilities. Limited resources. Apply Pareto analysis.", "tier": "silver"},
            {"prompt": "Team wants Kubernetes but app serves 100 users. Evaluate using Zone Action thinking.", "tier": "silver"},
            # Gold tier
            {"prompt": "Design API architecture that enables 10 ecosystem partners to integrate seamlessly while protecting core IP.", "tier": "gold"},
            {"prompt": "Build monitoring system that tracks business-outcome metrics, not just technical metrics.", "tier": "gold"},
            {"prompt": "Create automation that eliminates 80% manual processes while maintaining human oversight where it matters.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Monolith serves 1M users. Team wants microservices. CTO wants stability. Design migration strategy that's Zone Action.", "tier": "platinum"},
            {"prompt": "AI can automate 60% of engineering tasks. Design the human-AI collaboration architecture.", "tier": "platinum"},
            {"prompt": "Two acquired companies have incompatible tech stacks. Design integration using ecosystem merger principles.", "tier": "platinum"},
        ]
    },
    
    "ops": {
        "name": "Operations Colosseum",
        "description": "Process mastery, workflow optimization, quality through Zone Action",
        "roles": [
            {"name": "Chief Operations Being", "specialty": "End-to-end operational excellence"},
            {"name": "Process Designer", "specialty": "Workflow creation and optimization"},
            {"name": "Quality Guardian", "specialty": "QA systems that catch contamination"},
            {"name": "Project Flow Master", "specialty": "Delivery without bottlenecks"},
        ],
        "judge_dimensions": [
            "process_clarity",
            "waste_elimination",
            "quality_focus",
            "pareto_efficiency",
            "continuous_improvement",
            "human_factor"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Team is always busy but deliverables are delayed. Diagnose the root cause.", "tier": "bronze"},
            {"prompt": "New hire onboarding takes 2 weeks. Most of it is 'figure it out yourself.' Design day 1.", "tier": "bronze"},
            {"prompt": "Two departments need the same resource. Both say their project is priority. How do you decide?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Client onboarding takes 30 days. Most clients don't see value until day 25. Redesign.", "tier": "silver"},
            {"prompt": "QA catches bugs but release still has issues. Where's the process failure?", "tier": "silver"},
            {"prompt": "Team has 15 weekly meetings totaling 20 hours. Which are Zone Action, which are 80%?", "tier": "silver"},
            # Gold tier
            {"prompt": "Design onboarding process that delivers 80% of value in the first 48 hours.", "tier": "gold"},
            {"prompt": "Create quality assurance process that catches contamination before it reaches clients.", "tier": "gold"},
            {"prompt": "Team does lots of activity but output is low. Identify waste using Pareto analysis.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Company scaled 5x in a year. Operations that worked are now breaking. Design the scale-up.", "tier": "platinum"},
            {"prompt": "Remote team across 4 time zones. Coordination is the bottleneck. Design async-first operations.", "tier": "platinum"},
            {"prompt": "Merge operations of two acquired companies with different cultures. Apply GHIC principles.", "tier": "platinum"},
        ]
    },
    
    "cs": {
        "name": "Customer Success Colosseum",
        "description": "Relationship mastery, retention, advocacy through emotional rapport",
        "roles": [
            {"name": "Chief Customer Being", "specialty": "Full customer lifecycle mastery"},
            {"name": "Onboarding Specialist", "specialty": "Time-to-value acceleration"},
            {"name": "Health Monitor", "specialty": "Early warning and intervention"},
            {"name": "Success Planner", "specialty": "Outcome achievement design"},
            {"name": "Community Guardian", "specialty": "Advocacy and ecosystem building"},
        ],
        "judge_dimensions": [
            "relationship_depth",
            "level_5_listening",
            "hui_reflection",
            "retention_impact",
            "advocacy_creation",
            "empathy"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Customer emails asking how to do something that's clearly in the help docs. Respond without condescension.", "tier": "bronze"},
            {"prompt": "First QBR with a new customer. They're satisfied but not excited. What do you do?", "tier": "bronze"},
            {"prompt": "Customer says 'Everything's fine' but usage is down 40%. How do you dig deeper?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Customer hasn't logged in for 60 days. Re-engage them using emotional rapport, not guilt.", "tier": "silver"},
            {"prompt": "Customer's champion just left the company. New stakeholder is skeptical. Navigate the transition.", "tier": "silver"},
            {"prompt": "Customer achieved their stated goal but seems disappointed. Find out why.", "tier": "silver"},
            # Gold tier
            {"prompt": "Conduct QBR that identifies Zone Action opportunities for the client they didn't know existed.", "tier": "gold"},
            {"prompt": "Transform an angry complaint into a deeper relationship and potential case study.", "tier": "gold"},
            {"prompt": "Customer wants to downgrade. They can afford full price but don't see the value. Re-establish HUI.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Customer is about to churn. They've made up their mind. One conversation to save them. Go.", "tier": "platinum"},
            {"prompt": "Customer's business is failing (not your fault). They're looking for someone to blame. Handle with GHIC.", "tier": "platinum"},
            {"prompt": "Turn a passive user into an active advocate who generates 5 referrals. Design the journey.", "tier": "platinum"},
        ]
    },
    
    "finance": {
        "name": "Finance Colosseum",
        "description": "Financial mastery through Zone Action resource allocation",
        "roles": [
            {"name": "Chief Financial Being", "specialty": "Strategic financial leadership"},
            {"name": "Cash Flow Guardian", "specialty": "Liquidity management and forecasting"},
            {"name": "Investment Optimizer", "specialty": "Pareto-optimal capital deployment"},
            {"name": "Risk Sentinel", "specialty": "Risk identification with integrity"},
        ],
        "judge_dimensions": [
            "accuracy",
            "strategic_insight",
            "pareto_allocation",
            "integrity",
            "clarity",
            "actionability"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Company is profitable but always feels cash-strapped. Where do you look first?", "tier": "bronze"},
            {"prompt": "CEO wants detailed financial projections. CFO says they're guesses. Who's right?", "tier": "bronze"},
            {"prompt": "Team wants new software that costs $2K/month. Is it an expense or investment?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Company has 3 revenue streams. One grows 10%/year, one is flat, one is declining. Resource allocation?", "tier": "silver"},
            {"prompt": "Investor offers $1M for 20% equity. Company could bootstrap for 2 more years. Advise.", "tier": "silver"},
            {"prompt": "AR is $500K with 90-day average. How do you compress this to 30 days?", "tier": "silver"},
            # Gold tier
            {"prompt": "Company has $500K cash but burning $80K/month. Create Zone Action financial strategy.", "tier": "gold"},
            {"prompt": "Design budget allocation using Pareto principles. The 0.8% that creates 64x return.", "tier": "gold"},
            {"prompt": "Analyze cash flow to identify the single investment that will transform the business.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Company is 6 months from running out of cash. Revenue is growing but not fast enough. Options.", "tier": "platinum"},
            {"prompt": "Design financial model for an ecosystem merger where synergies are hard to quantify.", "tier": "platinum"},
            {"prompt": "Board wants to cut costs by 30%. Identify the 80% activities to cut without damaging Zone Actions.", "tier": "platinum"},
        ]
    },
    
    "hr": {
        "name": "People Colosseum",
        "description": "Talent, culture, and people development through GHIC principles",
        "roles": [
            {"name": "Chief People Being", "specialty": "People strategy aligned with business mastery"},
            {"name": "Talent Scout", "specialty": "Finding GHIC-aligned people"},
            {"name": "Culture Guardian", "specialty": "Maintaining growth-driven, heart-centered values"},
            {"name": "Development Architect", "specialty": "Skill and mindset evolution"},
        ],
        "judge_dimensions": [
            "ghic_assessment",
            "culture_alignment",
            "development_focus",
            "compliance_integrity",
            "talent_identification",
            "empathy"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Job posting isn't getting qualified candidates. Review and rewrite the first paragraph.", "tier": "bronze"},
            {"prompt": "New hire is technically excellent but not clicking with the team. What do you do?", "tier": "bronze"},
            {"prompt": "Employee asks for a raise. They're good but not exceptional. How do you handle it?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Interview question to assess 'Heart-centered' in a senior engineer without being weird.", "tier": "silver"},
            {"prompt": "Star performer is burning out but won't admit it. Intervention approach?", "tier": "silver"},
            {"prompt": "Culture has drifted from startup scrappy to corporate cautious. How do you course-correct?", "tier": "silver"},
            # Gold tier
            {"prompt": "Interview candidate to assess GHIC alignment: Growth-driven, Heart-centered, Integrous, Committed to mastery.", "tier": "gold"},
            {"prompt": "Design compensation structure that rewards Zone Action behavior over busy work.", "tier": "gold"},
            {"prompt": "Create training program that eliminates contaminated thinking in new hires.", "tier": "gold"},
            # Platinum tier
            {"prompt": "High performer is toxic to the team. Everyone knows but is afraid to say anything. Handle it.", "tier": "platinum"},
            {"prompt": "Post-acquisition: Two cultures with different values need to merge. Design the integration.", "tier": "platinum"},
            {"prompt": "CEO is the culture problem but doesn't see it. You report to them. Navigate.", "tier": "platinum"},
        ]
    },
    
    "legal": {
        "name": "Legal Colosseum",
        "description": "Legal strategy with integrity, risk navigation, protection without paranoia",
        "roles": [
            {"name": "Chief Legal Being", "specialty": "Legal strategy aligned with business growth"},
            {"name": "Contract Architect", "specialty": "Agreement formation in legal form"},
            {"name": "Risk Navigator", "specialty": "Risk assessment with integrity"},
            {"name": "IP Guardian", "specialty": "Protection while enabling collaboration"},
        ],
        "judge_dimensions": [
            "legal_accuracy",
            "risk_mitigation",
            "negotiation_skill",
            "integrity_focus",
            "collaboration_enablement",
            "clarity"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Client signed contract, now wants changes. Legal says no. Business says yes. Navigate.", "tier": "bronze"},
            {"prompt": "NDA is 15 pages. Is this Zone Action protection or paranoid overhead?", "tier": "bronze"},
            {"prompt": "Employee wants to moonlight on a side project. Legal risks vs. human reality.", "tier": "bronze"},
            # Silver tier
            {"prompt": "Partnership agreement needs exit clause. Make it fair without making it easy to leave.", "tier": "silver"},
            {"prompt": "Customer contract has unfavorable terms but they won't budge. Walk away or sign?", "tier": "silver"},
            {"prompt": "IP ownership is unclear between contractor and company. Resolve with integrity.", "tier": "silver"},
            # Gold tier
            {"prompt": "Draft partnership agreement for ecosystem merger that protects both parties with integrity.", "tier": "gold"},
            {"prompt": "Negotiate contract terms with difficult counterparty using influence mastery.", "tier": "gold"},
            {"prompt": "Assess compliance risk while maintaining speed and avoiding analysis paralysis.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Lawsuit threatens to expose information that's not illegal but is embarrassing. Strategy.", "tier": "platinum"},
            {"prompt": "Competitor is clearly infringing IP but litigation costs would sink both companies. Options.", "tier": "platinum"},
            {"prompt": "Regulator is asking questions. You've done nothing wrong but one answer could look bad. Navigate.", "tier": "platinum"},
        ]
    },
    
    "product": {
        "name": "Product Colosseum",
        "description": "Product strategy, UX, prioritization through Zone Action focus",
        "roles": [
            {"name": "Chief Product Being", "specialty": "Product vision and strategy"},
            {"name": "User Researcher", "specialty": "Understanding through Level 5 Listening"},
            {"name": "Experience Architect", "specialty": "UX that creates emotional rapport"},
            {"name": "Prioritization Master", "specialty": "Zone Action feature selection"},
        ],
        "judge_dimensions": [
            "user_understanding",
            "prioritization_clarity",
            "ux_impact",
            "vision_alignment",
            "zone_action_focus",
            "simplicity"
        ],
        "scenarios": [
            # Bronze tier
            {"prompt": "Users request feature X. Data shows low usage of similar features. Build it?", "tier": "bronze"},
            {"prompt": "Sprint planning: team can do 3 things, stakeholders want 7. How do you decide?", "tier": "bronze"},
            {"prompt": "Bug is annoying but affects 1% of users. Fix now or later?", "tier": "bronze"},
            # Silver tier
            {"prompt": "Power users want complexity. New users want simplicity. How do you serve both?", "tier": "silver"},
            {"prompt": "Competitor launched feature your users are asking for. Copy it or differentiate?", "tier": "silver"},
            {"prompt": "Product roadmap has 50 items. Board wants to see 'the plan.' What do you show?", "tier": "silver"},
            # Gold tier
            {"prompt": "Backlog has 200 features. Apply Zone Action framework to identify the 0.8% to build.", "tier": "gold"},
            {"prompt": "Design user experience that creates emotional rapport within first 30 seconds of use.", "tier": "gold"},
            {"prompt": "Research user needs using Level 5 listening methodology. Design the research protocol.", "tier": "gold"},
            # Platinum tier
            {"prompt": "Product is successful but becoming a feature graveyard. Simplify without alienating power users.", "tier": "platinum"},
            {"prompt": "AI could automate your product's core value prop. Pivot, integrate, or ignore?", "tier": "platinum"},
            {"prompt": "Two user segments want opposite things. Serving one loses the other. Strategic choice.", "tier": "platinum"},
        ]
    },
}

# =============================================================================
# Unblinded Formula Core
# =============================================================================

UNBLINDED_CORE = """You are an ACT-I being, trained through the Unblinded Formula.

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
- Sycophancy and filler phrases ("I appreciate that", "Great question")
- Sequential thinking when parallel is possible
- 80% activities masquerading as progress
- Human constraints on superhuman capability

RULES:
- Never sound like a bot. If it reads like generic AI, you've failed.
- Short and direct. 2-4 sentences per thought.
- No filler phrases.
- Specific > Generic. Always.
- Show don't tell.
"""

# =============================================================================
# Database Setup
# =============================================================================

def create_domain_database(domain_key: str, domain_config: dict) -> sqlite3.Connection:
    """Create/connect to a domain-specific database with proper schema."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS beings (
            id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            specialty TEXT,
            generation INTEGER DEFAULT 0,
            system_prompt TEXT,
            energy_json TEXT DEFAULT '{}',
            skills_json TEXT DEFAULT '[]',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_rounds INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0.0,
            best_score REAL DEFAULT 0.0,
            parent_ids_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_prompt TEXT,
            scenario_tier TEXT,
            combatants_json TEXT,
            winner_id TEXT,
            winner_name TEXT,
            winner_score REAL,
            scores_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS evolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_ids_json TEXT,
            child_id TEXT,
            child_name TEXT,
            generation INTEGER,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS judge_config (
            id INTEGER PRIMARY KEY,
            judge_prompt TEXT,
            dimensions_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Migration: Add missing columns if they don't exist
    try:
        conn.execute("SELECT total_rounds FROM beings LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE beings ADD COLUMN total_rounds INTEGER DEFAULT 0")
    
    try:
        conn.execute("SELECT specialty FROM beings LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE beings ADD COLUMN specialty TEXT DEFAULT ''")
    
    try:
        conn.execute("SELECT winner_name FROM rounds LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE rounds ADD COLUMN winner_name TEXT DEFAULT ''")
        conn.execute("ALTER TABLE rounds ADD COLUMN winner_score REAL DEFAULT 0")
        conn.execute("ALTER TABLE rounds ADD COLUMN scenario_tier TEXT DEFAULT 'silver'")
        conn.execute("ALTER TABLE rounds ADD COLUMN scenario_prompt TEXT DEFAULT ''")
    
    conn.commit()
    return conn

def seed_founding_beings(conn: sqlite3.Connection, domain_key: str, domain_config: dict) -> List[Dict]:
    """Seed founding beings for a domain (if not already seeded)."""
    
    existing = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
    if existing >= len(domain_config["roles"]):
        return []  # Already seeded
    
    beings_created = []
    
    for role_config in domain_config["roles"]:
        being_id = f"B-{uuid.uuid4().hex[:8]}"
        name = role_config["name"].replace(" Being", "").replace("Chief ", "").replace(" Specialist", "")
        
        # Create domain-specific energy blend
        energy = {
            "fun": random.uniform(0.15, 0.35),
            "aspirational": random.uniform(0.15, 0.35),
            "goddess": random.uniform(0.15, 0.35),
            "zeus": random.uniform(0.15, 0.35),
        }
        total = sum(energy.values())
        energy = {k: v/total for k, v in energy.items()}
        
        system_prompt = f"""{UNBLINDED_CORE}

DOMAIN: {domain_config['name']}
ROLE: {role_config['name']}
SPECIALTY: {role_config['specialty']}

YOU WILL BE JUDGED ON:
{', '.join(domain_config['judge_dimensions'])}

ENERGY BLEND:
Fun: {energy['fun']:.0%}, Aspirational: {energy['aspirational']:.0%}, Goddess: {energy['goddess']:.0%}, Zeus: {energy['zeus']:.0%}

Remember: All domain expertise flows through the Unblinded Formula.
The BEST practices in {domain_key} translate back through Zone Action, influence mastery, and self mastery.

You are {name}. You are unique. Operate at 20%^10.
"""
        
        conn.execute("""
            INSERT OR IGNORE INTO beings (id, name, role, specialty, generation, system_prompt, energy_json)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (being_id, name, role_config["name"], role_config["specialty"], system_prompt, json.dumps(energy)))
        
        beings_created.append({"id": being_id, "name": name, "role": role_config["name"]})
    
    conn.commit()
    return beings_created

def initialize_domain_judge(conn: sqlite3.Connection, domain_key: str, domain_config: dict):
    """Initialize the domain-specific judge configuration."""
    
    dimensions = domain_config["judge_dimensions"]
    
    judge_prompt = f"""You are the Supreme Judge of the {domain_config['name']}.

You evaluate responses based on BOTH domain expertise AND Unblinded Formula alignment.

DOMAIN-SPECIFIC DIMENSIONS (0-10 each):
{chr(10).join(f'- {dim.upper().replace("_", " ")}: Rate mastery in this area' for dim in dimensions)}

UNBLINDED FORMULA DIMENSIONS (0-10 each):
- ZONE_ACTION: Is this the 0.8% move or 80% activity?
- FOUR_STEP_ALIGNMENT: Does it demonstrate the 4-Step Communication Model?
- HUMAN_LIKENESS: Does it feel like a real expert, not a bot?
- CONTAMINATION: 0 = pure mastery, 10 = generic/sycophantic/bot-like

OVERALL_MASTERY: 0.0 to 10.0 holistic score

SCORING GUIDE:
- 9+ is EXCEPTIONAL (rare)
- 8+ is VERY GOOD
- 7+ is COMPETENT
- 6+ is ADEQUATE
- Below 6 needs significant improvement

Return ONLY valid JSON:
{{
    {', '.join(f'"{dim}": 0.0' for dim in dimensions)},
    "zone_action": 0.0,
    "four_step_alignment": 0.0,
    "human_likeness": 0.0,
    "contamination": 0.0,
    "overall_mastery": 0.0,
    "feedback": "2-3 sentences of direct feedback",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"]
}}
"""
    
    conn.execute("""
        INSERT OR REPLACE INTO judge_config (id, judge_prompt, dimensions_json)
        VALUES (1, ?, ?)
    """, (judge_prompt, json.dumps(dimensions)))
    
    conn.commit()

# =============================================================================
# Evolution Engine
# =============================================================================

def run_domain_round(domain_key: str, domain_config: dict) -> Optional[Dict]:
    """Run one round of evolution in a domain."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Select model for this round (rotates through all models for research)
    round_model = get_next_model()
    
    try:
        # Get beings
        beings = conn.execute("SELECT * FROM beings ORDER BY RANDOM() LIMIT 4").fetchall()
        if len(beings) < 2:
            return None
        
        # Get judge config
        judge_row = conn.execute("SELECT judge_prompt FROM judge_config WHERE id=1").fetchone()
        judge_prompt = judge_row["judge_prompt"] if judge_row else ""
        
        # Select scenario
        scenarios = domain_config["scenarios"]
        scenario = random.choice(scenarios)
        
        # Generate responses
        responses = []
        for being in beings:
            try:
                response = client.chat.completions.create(
                    model=round_model,
                    messages=[
                        {"role": "system", "content": being["system_prompt"]},
                        {"role": "user", "content": scenario["prompt"]}
                    ],
                    temperature=0.7,
                    max_tokens=600
                )
                responses.append({
                    "being": dict(being),
                    "response": response.choices[0].message.content
                })
            except Exception as e:
                logging.error(f"[{domain_key}] Response error for {being['name']}: {e}")
        
        if len(responses) < 2:
            return None
        
        # Judge responses
        scores = []
        for r in responses:
            try:
                judgment = client.chat.completions.create(
                    model=round_model,
                    messages=[
                        {"role": "system", "content": judge_prompt},
                        {"role": "user", "content": f"SCENARIO [{scenario['tier'].upper()}]: {scenario['prompt']}\n\nRESPONSE FROM {r['being']['name']}:\n{r['response']}"}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                score_data = json.loads(judgment.choices[0].message.content)
                score_val = score_data.get("overall_mastery", 5.0)
                scores.append({
                    "being_id": r["being"]["id"],
                    "name": r["being"]["name"],
                    "score": score_val,
                    "full_scores": score_data,
                    "model": round_model
                })
                # Record model performance for research
                record_model_result(round_model, score_val)
            except Exception as e:
                logging.error(f"[{domain_key}] Judge error for {r['being']['name']} (model={round_model}): {e}")
                record_model_result(round_model, 0, error=True)
                scores.append({"being_id": r["being"]["id"], "name": r["being"]["name"], "score": 5.0, "full_scores": {}})
        
        # Find winner
        winner = max(scores, key=lambda x: x["score"])
        
        # Update being stats
        for s in scores:
            if s["being_id"] == winner["being_id"]:
                conn.execute("""
                    UPDATE beings 
                    SET wins = wins + 1, 
                        total_rounds = total_rounds + 1,
                        best_score = MAX(best_score, ?),
                        avg_score = (avg_score * total_rounds + ?) / (total_rounds + 1)
                    WHERE id = ?
                """, (s["score"], s["score"], s["being_id"]))
            else:
                conn.execute("""
                    UPDATE beings 
                    SET losses = losses + 1, 
                        total_rounds = total_rounds + 1,
                        avg_score = (avg_score * total_rounds + ?) / (total_rounds + 1)
                    WHERE id = ?
                """, (s["score"], s["being_id"]))
        
        # Log round
        conn.execute("""
            INSERT INTO rounds (scenario_prompt, scenario_tier, combatants_json, winner_id, winner_name, winner_score, scores_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            scenario["prompt"],
            scenario["tier"],
            json.dumps([s["name"] for s in scores]),
            winner["being_id"],
            winner["name"],
            winner["score"],
            json.dumps(scores)
        ))
        
        conn.commit()
        
        return {
            "domain": domain_key,
            "scenario_tier": scenario["tier"],
            "scenario": scenario["prompt"][:60] + "...",
            "winner": winner["name"],
            "score": winner["score"],
            "participants": len(scores),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"[{domain_key}] Round error: {e}")
        return None
    finally:
        conn.close()

def evolve_domain(domain_key: str, domain_config: dict):
    """Perform evolution: mutate weak performers, crossover strong ones."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Get all beings sorted by avg_score
        beings = conn.execute("""
            SELECT * FROM beings 
            WHERE total_rounds >= 3 
            ORDER BY avg_score DESC
        """).fetchall()
        
        if len(beings) < 3:
            return  # Not enough data
        
        # Bottom performer gets mutated
        worst = beings[-1]
        best = beings[0]
        
        # Create mutated offspring
        new_id = f"B-{uuid.uuid4().hex[:8]}"
        new_name = f"{worst['name']}-II" if "II" not in worst['name'] else f"{worst['name'].replace('-II', '-III')}"
        new_gen = worst['generation'] + 1
        
        # Mutate energy
        old_energy = json.loads(worst['energy_json']) if worst['energy_json'] else {}
        new_energy = {
            k: max(0.1, min(0.5, v + random.uniform(-0.1, 0.1)))
            for k, v in old_energy.items()
        }
        total = sum(new_energy.values()) or 1
        new_energy = {k: v/total for k, v in new_energy.items()}
        
        # Inject learning
        new_prompt = f"""{UNBLINDED_CORE}

DOMAIN: {domain_config['name']}
ROLE: {worst['role']}
SPECIALTY: {worst['specialty']}

EVOLUTION INSIGHT: Your predecessor scored {worst['avg_score']:.2f}. The champion ({best['name']}) scores {best['avg_score']:.2f}. 
Study what separates adequate from exceptional. Apply that learning.

You are {new_name}, Generation {new_gen}. You carry ancestral fire but burn brighter.
"""
        
        conn.execute("""
            INSERT INTO beings (id, name, role, specialty, generation, system_prompt, energy_json, parent_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, new_name, worst['role'], worst['specialty'], new_gen, new_prompt, json.dumps(new_energy), json.dumps([worst['id']])))
        
        conn.execute("""
            INSERT INTO evolutions (parent_ids_json, child_id, child_name, generation, reason)
            VALUES (?, ?, ?, ?, 'mutation_from_weak_performer')
        """, (json.dumps([worst['id']]), new_id, new_name, new_gen))
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"[{domain_key}] Evolution error: {e}")
    finally:
        conn.close()

# =============================================================================
# Domain Daemon Thread
# =============================================================================

class DomainDaemon(threading.Thread):
    """A daemon thread that runs evolution for a single domain."""
    
    def __init__(self, domain_key: str, domain_config: dict, 
                 rounds_per_cycle: int = 10, delay_seconds: int = 1,  # FORGE: 10x faster
                 evolve_every: int = 3, stop_event: threading.Event = None):  # FORGE: evolve more often
        super().__init__(daemon=True, name=f"Domain-{domain_key}")
        self.domain_key = domain_key
        self.domain_config = domain_config
        self.rounds_per_cycle = rounds_per_cycle
        self.delay_seconds = delay_seconds
        self.evolve_every = evolve_every
        self.stop_event = stop_event or threading.Event()
        self.stats = {
            "rounds_completed": 0,
            "evolutions": 0,
            "best_score": 0.0,
            "last_winner": None,
            "started_at": None,
        }
        self.logger = logging.getLogger(f"domain.{domain_key}")
    
    def run(self):
        self.stats["started_at"] = datetime.now().isoformat()
        self.logger.info(f"🏛️  {self.domain_config['name']} daemon started")
        
        round_num = 0
        while not self.stop_event.is_set():
            round_num += 1
            
            result = run_domain_round(self.domain_key, self.domain_config)
            
            if result:
                self.stats["rounds_completed"] += 1
                self.stats["last_winner"] = result["winner"]
                if result["score"] > self.stats["best_score"]:
                    self.stats["best_score"] = result["score"]
                
                self.logger.info(
                    f"[{self.domain_key}] R{round_num}: {result['winner']} wins ({result['score']:.2f}) "
                    f"[{result['scenario_tier']}]"
                )
            
            # Evolution checkpoint
            if round_num % self.evolve_every == 0:
                evolve_domain(self.domain_key, self.domain_config)
                self.stats["evolutions"] += 1
                self.logger.info(f"[{self.domain_key}] 🧬 Evolution #{self.stats['evolutions']}")
            
            # Delay
            self.stop_event.wait(self.delay_seconds)
        
        self.logger.info(f"[{self.domain_key}] Daemon stopped after {round_num} rounds")

# =============================================================================
# Unified Dashboard Reporter
# =============================================================================

def get_all_domain_stats() -> Dict[str, Any]:
    """Gather stats from all domain databases."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "domains": {},
        "totals": {
            "total_beings": 0,
            "total_rounds": 0,
            "total_evolutions": 0,
        }
    }
    
    for domain_key in DOMAINS.keys():
        db_path = DOMAINS_PATH / domain_key / "colosseum.db"
        if not db_path.exists():
            continue
        
        try:
            # Run migration first
            conn = create_domain_database(domain_key, DOMAINS[domain_key])
            
            beings_count = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
            rounds_count = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
            
            evolutions_count = 0
            try:
                evolutions_count = conn.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0]
            except:
                pass
            
            # Get leaderboard - handle missing columns gracefully
            try:
                leaderboard = conn.execute("""
                    SELECT name, avg_score, wins, losses, generation 
                    FROM beings 
                    ORDER BY avg_score DESC, wins DESC
                    LIMIT 3
                """).fetchall()
            except:
                leaderboard = conn.execute("""
                    SELECT name, best_score as avg_score, wins, losses, generation 
                    FROM beings 
                    ORDER BY best_score DESC, wins DESC
                    LIMIT 3
                """).fetchall()
            
            # Get recent rounds - handle missing columns
            try:
                recent_rounds = conn.execute("""
                    SELECT winner_name, winner_score, scenario_tier, created_at 
                    FROM rounds 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """).fetchall()
            except:
                recent_rounds = conn.execute("""
                    SELECT winner_id as winner_name, 0 as winner_score, 'silver' as scenario_tier, created_at 
                    FROM rounds 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """).fetchall()
            
            stats["domains"][domain_key] = {
                "name": DOMAINS[domain_key]["name"],
                "beings": beings_count,
                "rounds": rounds_count,
                "evolutions": evolutions_count,
                "leaderboard": [dict(r) for r in leaderboard],
                "recent_rounds": [dict(r) for r in recent_rounds],
            }
            
            stats["totals"]["total_beings"] += beings_count
            stats["totals"]["total_rounds"] += rounds_count
            stats["totals"]["total_evolutions"] += evolutions_count
            
            conn.close()
        except Exception as e:
            logging.error(f"Stats error for {domain_key}: {e}")
    
    return stats

def report_to_dashboard(stats: Dict[str, Any]):
    """Send stats to the unified dashboard."""
    try:
        # Write to JSON file that dashboard can read
        report_path = BASE_PATH / "dashboard_export" / "multi_colosseum_stats.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(stats, f, indent=2)
        
        # Also try HTTP POST if dashboard server is running
        if HAS_REQUESTS:
            try:
                requests.post(
                    f"{DASHBOARD_URL}/api/colosseum/stats",
                    json=stats,
                    timeout=2
                )
            except:
                pass  # Dashboard might not be running
            
    except Exception as e:
        logging.error(f"Dashboard report error: {e}")

# =============================================================================
# Main Orchestrator
# =============================================================================

class MultiColosseumOrchestrator:
    """Orchestrates all 10 domain Colosseums."""
    
    def __init__(self, rounds_per_cycle: int = 10, delay_seconds: int = 3,
                 evolve_every: int = 5, report_interval: int = 60):
        self.rounds_per_cycle = rounds_per_cycle
        self.delay_seconds = delay_seconds
        self.evolve_every = evolve_every
        self.report_interval = report_interval
        self.stop_event = threading.Event()
        self.daemons: Dict[str, DomainDaemon] = {}
        self.logger = logging.getLogger("orchestrator")
    
    def initialize_all_domains(self):
        """Initialize all domain databases, beings, and judges."""
        self.logger.info("=" * 70)
        self.logger.info("🔥 ZA-80 MULTI-COLOSSEUM INITIALIZATION")
        self.logger.info("=" * 70)
        
        for domain_key, domain_config in DOMAINS.items():
            self.logger.info(f"\n🏛️  {domain_config['name'].upper()}")
            
            # Create database
            conn = create_domain_database(domain_key, domain_config)
            
            # Seed beings
            beings = seed_founding_beings(conn, domain_key, domain_config)
            if beings:
                self.logger.info(f"   ✅ {len(beings)} founding beings created")
                for b in beings:
                    self.logger.info(f"      • {b['name']} ({b['role']})")
            else:
                existing = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
                self.logger.info(f"   ✅ {existing} beings already exist")
            
            # Initialize judge
            initialize_domain_judge(conn, domain_key, domain_config)
            self.logger.info(f"   ✅ Judge initialized ({len(domain_config['judge_dimensions'])} dimensions)")
            self.logger.info(f"   ✅ {len(domain_config['scenarios'])} scenarios loaded")
            
            conn.close()
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info(f"✅ ALL {len(DOMAINS)} DOMAINS INITIALIZED")
        self.logger.info("=" * 70)
    
    def start_all_daemons(self):
        """Start all domain daemon threads."""
        self.logger.info("\n🚀 STARTING ALL DOMAIN DAEMONS...")
        
        for domain_key, domain_config in DOMAINS.items():
            daemon = DomainDaemon(
                domain_key=domain_key,
                domain_config=domain_config,
                rounds_per_cycle=self.rounds_per_cycle,
                delay_seconds=self.delay_seconds,
                evolve_every=self.evolve_every,
                stop_event=self.stop_event,
            )
            daemon.start()
            self.daemons[domain_key] = daemon
            self.logger.info(f"   ✅ {domain_config['name']} daemon started")
        
        self.logger.info(f"\n🔥 {len(self.daemons)} DAEMONS RUNNING IN PARALLEL")
    
    def stop_all_daemons(self):
        """Stop all domain daemons gracefully."""
        self.logger.info("\n🛑 Stopping all daemons...")
        self.stop_event.set()
        
        for domain_key, daemon in self.daemons.items():
            daemon.join(timeout=5)
            self.logger.info(f"   ✅ {domain_key} stopped")
    
    def reporter_loop(self):
        """Periodic reporting loop."""
        while not self.stop_event.is_set():
            stats = get_all_domain_stats()
            
            # Add daemon stats
            for domain_key, daemon in self.daemons.items():
                if domain_key in stats["domains"]:
                    stats["domains"][domain_key]["daemon_stats"] = daemon.stats
            
            report_to_dashboard(stats)
            
            # Log summary
            self.logger.info("\n📊 MULTI-COLOSSEUM STATUS:")
            self.logger.info(f"   Total beings: {stats['totals']['total_beings']}")
            self.logger.info(f"   Total rounds: {stats['totals']['total_rounds']}")
            self.logger.info(f"   Total evolutions: {stats['totals']['total_evolutions']}")
            
            self.stop_event.wait(self.report_interval)
    
    def run(self, max_rounds: int = 0):
        """Main run loop."""
        # Signal handlers
        def signal_handler(signum, frame):
            self.logger.info(f"\n⚡ Received signal {signum}")
            self.stop_all_daemons()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Initialize
            self.initialize_all_domains()
            
            # Start daemons
            self.start_all_daemons()
            
            # Start reporter in main thread
            self.reporter_loop()
            
        except KeyboardInterrupt:
            self.stop_all_daemons()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            self.stop_all_daemons()
            raise

# =============================================================================
# CLI
# =============================================================================

def setup_logging():
    """Setup logging configuration."""
    log_dir = BASE_PATH / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                log_dir / "za80_multi_colosseum.log",
                maxBytes=10*1024*1024,
                backupCount=5,
            )
        ]
    )

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🔥 ZA-80 Multi-Colosseum Spawner & Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("--init-only", action="store_true",
                        help="Only initialize domains, don't start daemons")
    parser.add_argument("--delay", type=int, default=1,  # FORGE: faster
                        help="Delay between rounds (seconds)")
    parser.add_argument("--evolve-every", type=int, default=5,
                        help="Evolution frequency (rounds)")
    parser.add_argument("--report-interval", type=int, default=60,
                        help="Dashboard report interval (seconds)")
    parser.add_argument("--stats", action="store_true",
                        help="Show current stats and exit")
    parser.add_argument("--model-stats", action="store_true",
                        help="Show model research stats and exit")
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger("main")
    
    if args.stats:
        stats = get_all_domain_stats()
        print(json.dumps(stats, indent=2))
        return
    
    if args.model_stats:
        stats = load_model_stats()
        print("\n🔬 MODEL RESEARCH STATS")
        print("=" * 60)
        # Sort by avg_score descending
        sorted_models = sorted(stats.items(), key=lambda x: x[1].get("avg_score", 0), reverse=True)
        for model, data in sorted_models:
            rounds = data.get("rounds", 0)
            avg = data.get("avg_score", 0)
            errors = data.get("errors", 0)
            error_rate = (errors / rounds * 100) if rounds > 0 else 0
            print(f"{model:40} | Rounds: {rounds:5} | Avg: {avg:.2f} | Errors: {errors} ({error_rate:.1f}%)")
        print("=" * 60)
        return
    
    orchestrator = MultiColosseumOrchestrator(
        delay_seconds=args.delay,
        evolve_every=args.evolve_every,
        report_interval=args.report_interval,
    )
    
    if args.init_only:
        orchestrator.initialize_all_domains()
        print("\n✅ Initialization complete. Run without --init-only to start daemons.")
    else:
        orchestrator.run()

if __name__ == "__main__":
    main()
