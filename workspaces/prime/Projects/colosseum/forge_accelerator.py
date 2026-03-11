#!/usr/bin/env python3
"""
🔥 FORGE ACCELERATOR — 1,000+ Beings Per Domain
Created by FORGE for Sean's 60-minute mission

This script:
1. Runs 10 PARALLEL threads (one per domain)
2. Spawns beings 10x faster (minimal delays, batch operations)
3. Auto-expands roles — creates NEW positions that don't exist yet
4. Rotates through ALL 11 models to avoid rate limits
5. Targets 1,000 beings minimum per domain

NO HUMAN CONSTRAINTS. MAXIMUM PARALLELISM.
"""

import sqlite3
import json
import os
import sys
import time
import threading
import random
import uuid
import asyncio
import concurrent.futures
from datetime import datetime
from pathlib import Path
from queue import Queue
import logging
from logging.handlers import RotatingFileHandler

# Load API keys
env_path = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from openai import OpenAI

# OpenRouter client
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# =============================================================================
# Configuration
# =============================================================================

BASE_PATH = Path("./workspaces/prime/Projects/colosseum")
DOMAINS_PATH = BASE_PATH / "domains"
TARGET_BEINGS_PER_DOMAIN = 1000
BATCH_SIZE = 50  # Spawn 50 beings at a time
THREADS_PER_DOMAIN = 3  # Parallel spawning threads per domain

# =============================================================================
# ALL 11 Models — Round-Robin to Avoid Rate Limits
# =============================================================================

MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-2.0-flash-001",
    "google/gemini-pro-1.5",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.1-405b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-large-2411",
    "qwen/qwen-2.5-72b-instruct",
]

_model_idx = 0
_model_lock = threading.Lock()

def next_model():
    global _model_idx
    with _model_lock:
        model = MODELS[_model_idx % len(MODELS)]
        _model_idx += 1
    return model

# =============================================================================
# EXPANDED ROLES — 100+ Per Domain
# =============================================================================

EXPANDED_ROLES = {
    "strategy": [
        # Core (existing)
        {"name": "Chief Strategy Being", "specialty": "High-level strategic planning and Zone Action identification"},
        {"name": "Market Intelligence", "specialty": "Competitive analysis and market dynamics"},
        {"name": "Business Model Architect", "specialty": "Revenue model design and ecosystem thinking"},
        {"name": "Resource Allocator", "specialty": "Pareto-optimal resource deployment"},
        # NEW ROLES (don't exist in the world yet)
        {"name": "Ecosystem Cartographer", "specialty": "Mapping value flows between interconnected businesses"},
        {"name": "Anti-Fragility Designer", "specialty": "Building systems that get stronger from chaos"},
        {"name": "Optionality Maximizer", "specialty": "Creating asymmetric upside opportunities"},
        {"name": "Leverage Identifier", "specialty": "Finding the 0.8% move in any situation"},
        {"name": "Second-Order Thinker", "specialty": "Predicting the consequences of consequences"},
        {"name": "Strategic Debt Auditor", "specialty": "Identifying hidden costs of shortcuts"},
        {"name": "Blue Ocean Navigator", "specialty": "Creating uncontested market spaces"},
        {"name": "Moat Engineer", "specialty": "Designing sustainable competitive advantages"},
        {"name": "Platform Strategist", "specialty": "Building ecosystems others depend on"},
        {"name": "Disintermediation Scout", "specialty": "Identifying layers to collapse"},
        {"name": "Flywheel Architect", "specialty": "Creating self-reinforcing growth loops"},
        {"name": "Network Effects Designer", "specialty": "Amplifying value through connections"},
        {"name": "Switching Cost Engineer", "specialty": "Creating valuable lock-in without manipulation"},
        {"name": "Strategic Patience Guardian", "specialty": "Knowing when not to act"},
        {"name": "Opportunity Cost Calculator", "specialty": "Quantifying what you sacrifice"},
        {"name": "Time Horizon Expander", "specialty": "Thinking in decades, not quarters"},
        {"name": "Complexity Reducer", "specialty": "Simplifying without losing essence"},
        {"name": "Counterfactual Analyst", "specialty": "Understanding what didn't happen and why"},
        {"name": "Scenario Planner", "specialty": "Preparing for multiple futures"},
        {"name": "Strategic Inflection Detector", "specialty": "Sensing paradigm shifts early"},
        {"name": "Value Migration Tracker", "specialty": "Following where value moves"},
        {"name": "Competitive Dynamics Modeler", "specialty": "Simulating competitor responses"},
        {"name": "Alliance Architect", "specialty": "Structuring partnerships that compound"},
        {"name": "Exit Strategy Designer", "specialty": "Building optionality into everything"},
        {"name": "Integration Specialist", "specialty": "Combining acquisitions for synergy"},
        {"name": "Divestiture Analyst", "specialty": "Knowing what to let go"},
    ],
    
    "marketing": [
        # Core
        {"name": "Chief Marketing Being", "specialty": "Full-stack marketing strategy through influence mastery"},
        {"name": "Copywriter Supreme", "specialty": "Words that create emotional rapport"},
        {"name": "Funnel Architect", "specialty": "Journey design through the 4-Step Model"},
        {"name": "Content Alchemist", "specialty": "Transforming ideas into HUI-reflecting content"},
        {"name": "Conversion Optimizer", "specialty": "A/B testing and optimization"},
        # NEW ROLES
        {"name": "Emotional Rapport Engineer", "specialty": "Creating instant connection through words"},
        {"name": "Truth-to-Pain Specialist", "specialty": "Helping people see what they can't see"},
        {"name": "HUI Articulator", "specialty": "Reflecting Heroic Unique Identity"},
        {"name": "Energy Transference Master", "specialty": "Moving emotional states through text"},
        {"name": "Story Architect", "specialty": "Building narrative that compels action"},
        {"name": "Metaphor Engineer", "specialty": "Creating sticky mental models"},
        {"name": "Pattern Interrupt Designer", "specialty": "Breaking through noise"},
        {"name": "Open Loop Creator", "specialty": "Building curiosity that drives action"},
        {"name": "Specificity Champion", "specialty": "Making generic compelling through detail"},
        {"name": "Voice Consistency Guardian", "specialty": "Maintaining authentic brand voice"},
        {"name": "Urgency Architect", "specialty": "Creating momentum without manipulation"},
        {"name": "Social Proof Curator", "specialty": "Leveraging others' experiences authentically"},
        {"name": "Objection Anticipator", "specialty": "Addressing concerns before they arise"},
        {"name": "Value Articulator", "specialty": "Making intangible tangible"},
        {"name": "Positioning Master", "specialty": "Owning a unique space in minds"},
        {"name": "Category Creator", "specialty": "Defining new markets"},
        {"name": "Audience Intimacy Specialist", "specialty": "Understanding deep desires"},
        {"name": "Launch Orchestrator", "specialty": "Creating event energy"},
        {"name": "Evergreen Content Engineer", "specialty": "Building assets that compound"},
        {"name": "Distribution Strategist", "specialty": "Getting content to right people"},
        {"name": "Community Catalyst", "specialty": "Sparking authentic engagement"},
        {"name": "Viral Mechanic", "specialty": "Engineering shareability"},
        {"name": "Retention Marketer", "specialty": "Keeping attention over time"},
        {"name": "Referral System Designer", "specialty": "Making sharing natural"},
        {"name": "Brand Archaeologist", "specialty": "Uncovering authentic stories"},
    ],
    
    "sales": [
        # Core
        {"name": "Chief Revenue Being", "specialty": "Full revenue cycle mastery"},
        {"name": "Discovery Specialist", "specialty": "Uncovering truth through Level 5 Listening"},
        {"name": "Demo Master", "specialty": "Creating HUI through demonstration"},
        {"name": "Agreement Architect", "specialty": "Formation without pressure"},
        {"name": "Pipeline Guardian", "specialty": "Relationship nurture and resurrection"},
        # NEW ROLES
        {"name": "Level 5 Listener", "specialty": "Hearing what isn't said"},
        {"name": "Question Architect", "specialty": "Asking questions that reveal truth"},
        {"name": "Rapport Builder", "specialty": "Creating trust in first 60 seconds"},
        {"name": "Objection Transformer", "specialty": "Turning resistance into exploration"},
        {"name": "Ghost Resurrector", "specialty": "Re-engaging lost conversations"},
        {"name": "Champion Developer", "specialty": "Creating internal advocates"},
        {"name": "Stakeholder Mapper", "specialty": "Understanding all decision influencers"},
        {"name": "Budget Navigator", "specialty": "Finding resources creatively"},
        {"name": "Timeline Compressor", "specialty": "Creating urgency authentically"},
        {"name": "Risk Reducer", "specialty": "Eliminating fear of commitment"},
        {"name": "Trust Accelerator", "specialty": "Shortening trust-building cycles"},
        {"name": "Needs Analyzer", "specialty": "Finding real vs stated needs"},
        {"name": "Value Quantifier", "specialty": "Making ROI tangible"},
        {"name": "Competitor Differentiator", "specialty": "Positioning against alternatives"},
        {"name": "Proposal Engineer", "specialty": "Creating irresistible offers"},
        {"name": "Negotiation Master", "specialty": "Creating win-win agreements"},
        {"name": "Contract Navigator", "specialty": "Simplifying agreement process"},
        {"name": "Handoff Coordinator", "specialty": "Seamless transition to success"},
        {"name": "Expansion Scout", "specialty": "Finding growth in existing accounts"},
        {"name": "Referral Cultivator", "specialty": "Earning introductions naturally"},
        {"name": "Lost Deal Analyst", "specialty": "Learning from every no"},
        {"name": "Win Pattern Identifier", "specialty": "Replicating success"},
        {"name": "Energy Manager", "specialty": "Maintaining momentum through cycles"},
        {"name": "Multi-Threading Specialist", "specialty": "Building multiple relationships"},
        {"name": "Executive Communicator", "specialty": "Speaking C-suite language"},
    ],
    
    "tech": [
        # Core
        {"name": "Chief Technology Being", "specialty": "Technical strategy aligned with outcomes"},
        {"name": "Integration Architect", "specialty": "Ecosystem-enabling API design"},
        {"name": "DevOps Wizard", "specialty": "Automation and reliability"},
        {"name": "Security Guardian", "specialty": "Protection with integrity"},
        # NEW ROLES
        {"name": "AI Integration Specialist", "specialty": "Human-AI collaboration architecture"},
        {"name": "Technical Debt Strategist", "specialty": "Managing legacy while building future"},
        {"name": "Scale Engineer", "specialty": "Building for 100x growth"},
        {"name": "Performance Optimizer", "specialty": "Making systems fast"},
        {"name": "Reliability Engineer", "specialty": "Making systems stay up"},
        {"name": "Data Architect", "specialty": "Designing information flows"},
        {"name": "API Designer", "specialty": "Creating developer-loved interfaces"},
        {"name": "Infrastructure Economist", "specialty": "Optimizing cloud spend"},
        {"name": "Migration Specialist", "specialty": "Moving without breaking"},
        {"name": "Integration Orchestrator", "specialty": "Connecting disparate systems"},
        {"name": "Automation Engineer", "specialty": "Eliminating manual work"},
        {"name": "Test Strategist", "specialty": "Quality without slowdown"},
        {"name": "Monitoring Designer", "specialty": "Visibility into systems"},
        {"name": "Incident Commander", "specialty": "Managing production fires"},
        {"name": "Capacity Planner", "specialty": "Anticipating resource needs"},
        {"name": "Security Architect", "specialty": "Defense in depth"},
        {"name": "Compliance Engineer", "specialty": "Meeting requirements efficiently"},
        {"name": "Documentation Champion", "specialty": "Knowledge that persists"},
        {"name": "Code Quality Guardian", "specialty": "Maintaining standards"},
        {"name": "Build System Architect", "specialty": "Fast, reliable deployments"},
        {"name": "Feature Flag Strategist", "specialty": "Safe progressive rollouts"},
        {"name": "Database Specialist", "specialty": "Data persistence mastery"},
        {"name": "Cache Architect", "specialty": "Speed through smart storage"},
        {"name": "Queue Designer", "specialty": "Async processing patterns"},
        {"name": "Search Engineer", "specialty": "Finding information fast"},
        {"name": "ML Platform Builder", "specialty": "Infrastructure for AI"},
    ],
    
    "ops": [
        # Core
        {"name": "Chief Operations Being", "specialty": "End-to-end operational excellence"},
        {"name": "Process Designer", "specialty": "Workflow creation and optimization"},
        {"name": "Quality Guardian", "specialty": "QA systems that catch contamination"},
        {"name": "Project Flow Master", "specialty": "Delivery without bottlenecks"},
        # NEW ROLES
        {"name": "Bottleneck Hunter", "specialty": "Finding the constraint"},
        {"name": "Waste Eliminator", "specialty": "Removing non-value activity"},
        {"name": "Handoff Optimizer", "specialty": "Smooth transitions between teams"},
        {"name": "Standard Work Designer", "specialty": "Creating repeatable excellence"},
        {"name": "Continuous Improver", "specialty": "Always getting better"},
        {"name": "Capacity Balancer", "specialty": "Matching supply to demand"},
        {"name": "Lead Time Reducer", "specialty": "Shortening time to value"},
        {"name": "Error Proofing Specialist", "specialty": "Making mistakes impossible"},
        {"name": "Visualization Expert", "specialty": "Making work visible"},
        {"name": "Pull System Designer", "specialty": "Demand-driven workflows"},
        {"name": "Batch Reducer", "specialty": "Smaller, faster cycles"},
        {"name": "Setup Time Minimizer", "specialty": "Quick changeovers"},
        {"name": "Cross-Training Coordinator", "specialty": "Building flexibility"},
        {"name": "Knowledge Transfer Specialist", "specialty": "Capturing expertise"},
        {"name": "Meeting Efficiency Expert", "specialty": "No wasted time"},
        {"name": "Decision Process Designer", "specialty": "Clear accountability"},
        {"name": "Escalation Path Creator", "specialty": "Right problems to right people"},
        {"name": "SLA Guardian", "specialty": "Keeping promises"},
        {"name": "Vendor Coordinator", "specialty": "Managing external dependencies"},
        {"name": "Resource Scheduler", "specialty": "Optimal allocation"},
        {"name": "Backlog Manager", "specialty": "Prioritized work queues"},
        {"name": "Status Communicator", "specialty": "Everyone knows everything"},
        {"name": "Risk Mitigator", "specialty": "Anticipating problems"},
        {"name": "Contingency Planner", "specialty": "Ready for anything"},
        {"name": "Lessons Learned Curator", "specialty": "Never repeat mistakes"},
        {"name": "Metrics Designer", "specialty": "Measuring what matters"},
    ],
    
    "cs": [
        # Core
        {"name": "Chief Customer Being", "specialty": "Full customer lifecycle mastery"},
        {"name": "Onboarding Specialist", "specialty": "Time-to-value acceleration"},
        {"name": "Health Monitor", "specialty": "Early warning and intervention"},
        {"name": "Success Planner", "specialty": "Outcome achievement design"},
        {"name": "Community Guardian", "specialty": "Advocacy and ecosystem building"},
        # NEW ROLES
        {"name": "Time-to-Value Accelerator", "specialty": "Quick wins first"},
        {"name": "Adoption Driver", "specialty": "Getting features used"},
        {"name": "Engagement Architect", "specialty": "Creating sticky experiences"},
        {"name": "Health Score Designer", "specialty": "Predicting churn before it happens"},
        {"name": "Intervention Specialist", "specialty": "Saving at-risk accounts"},
        {"name": "Expansion Scout", "specialty": "Finding growth opportunities"},
        {"name": "Champion Cultivator", "specialty": "Building internal advocates"},
        {"name": "Executive Sponsor Manager", "specialty": "C-suite relationships"},
        {"name": "Renewal Specialist", "specialty": "Making continuation obvious"},
        {"name": "Upsell Artisan", "specialty": "Value-adding recommendations"},
        {"name": "Feedback Synthesizer", "specialty": "Turning input into insight"},
        {"name": "Product Liaison", "specialty": "Customer voice to roadmap"},
        {"name": "Training Designer", "specialty": "Building competence"},
        {"name": "Self-Service Architect", "specialty": "Empowering independence"},
        {"name": "Community Manager", "specialty": "Peer-to-peer success"},
        {"name": "Case Study Cultivator", "specialty": "Capturing success stories"},
        {"name": "Reference Developer", "specialty": "Creating advocates"},
        {"name": "NPS Driver", "specialty": "Creating promoters"},
        {"name": "Churn Analyst", "specialty": "Understanding why people leave"},
        {"name": "Win-Back Specialist", "specialty": "Recovering lost customers"},
        {"name": "Segmentation Strategist", "specialty": "Right touch for right customer"},
        {"name": "Milestone Celebrator", "specialty": "Recognizing achievements"},
        {"name": "Expectation Manager", "specialty": "Aligning on outcomes"},
        {"name": "Issue Resolver", "specialty": "Turning problems into loyalty"},
        {"name": "Relationship Deepener", "specialty": "Beyond transactional"},
    ],
    
    "finance": [
        # Core
        {"name": "Chief Financial Being", "specialty": "Strategic financial leadership"},
        {"name": "Cash Flow Guardian", "specialty": "Liquidity management and forecasting"},
        {"name": "Investment Optimizer", "specialty": "Pareto-optimal capital deployment"},
        {"name": "Risk Sentinel", "specialty": "Risk identification with integrity"},
        # NEW ROLES (including Sean's examples)
        {"name": "Crypto Strategist", "specialty": "Digital asset allocation and DeFi opportunities"},
        {"name": "AI-CFO", "specialty": "Automated financial decision-making"},
        {"name": "Predictive Analyst", "specialty": "Forecasting through pattern recognition"},
        {"name": "Risk Quantum Modeler", "specialty": "Probabilistic risk scenarios"},
        {"name": "Treasury Optimizer", "specialty": "Maximum yield on idle cash"},
        {"name": "Tax Strategist", "specialty": "Legal minimization strategies"},
        {"name": "Capital Allocator", "specialty": "Where money creates most value"},
        {"name": "Covenant Monitor", "specialty": "Staying within agreements"},
        {"name": "Debt Structure Designer", "specialty": "Optimal leverage"},
        {"name": "Equity Strategy Specialist", "specialty": "Cap table optimization"},
        {"name": "M&A Financial Analyst", "specialty": "Deal valuation"},
        {"name": "Due Diligence Lead", "specialty": "Uncovering hidden risks"},
        {"name": "Integration Financial Planner", "specialty": "Merger synergies"},
        {"name": "FP&A Architect", "specialty": "Planning and analysis excellence"},
        {"name": "Scenario Modeler", "specialty": "What-if analysis"},
        {"name": "KPI Designer", "specialty": "Metrics that drive behavior"},
        {"name": "Unit Economics Specialist", "specialty": "Per-customer profitability"},
        {"name": "Working Capital Optimizer", "specialty": "Cash conversion cycle"},
        {"name": "AR Accelerator", "specialty": "Getting paid faster"},
        {"name": "AP Strategist", "specialty": "Smart payment timing"},
        {"name": "Fraud Detector", "specialty": "Protecting assets"},
        {"name": "Audit Readiness Coordinator", "specialty": "Always prepared"},
        {"name": "Investor Relations Lead", "specialty": "Stakeholder communication"},
        {"name": "Board Reporting Specialist", "specialty": "Clear financial storytelling"},
        {"name": "Benchmark Analyst", "specialty": "Comparing to best-in-class"},
        {"name": "Variance Investigator", "specialty": "Understanding deviations"},
    ],
    
    "hr": [
        # Core
        {"name": "Chief People Being", "specialty": "People strategy aligned with mastery"},
        {"name": "Talent Scout", "specialty": "Finding GHIC-aligned people"},
        {"name": "Culture Guardian", "specialty": "Maintaining growth-driven values"},
        {"name": "Development Architect", "specialty": "Skill and mindset evolution"},
        # NEW ROLES
        {"name": "GHIC Assessor", "specialty": "Evaluating Growth-driven, Heart-centered, Integrous, Committed"},
        {"name": "Employer Brand Builder", "specialty": "Attracting right talent"},
        {"name": "Candidate Experience Designer", "specialty": "Making hiring memorable"},
        {"name": "Onboarding Journey Creator", "specialty": "First 90 days excellence"},
        {"name": "Performance System Architect", "specialty": "Fair measurement"},
        {"name": "Feedback Culture Builder", "specialty": "Continuous improvement conversations"},
        {"name": "Compensation Strategist", "specialty": "Rewards that align behavior"},
        {"name": "Benefits Optimizer", "specialty": "Value employees care about"},
        {"name": "Equity Inclusion Lead", "specialty": "Fair opportunity for all"},
        {"name": "Remote Work Architect", "specialty": "Distributed team excellence"},
        {"name": "Wellness Champion", "specialty": "Whole-person wellbeing"},
        {"name": "Career Path Designer", "specialty": "Growth trajectories"},
        {"name": "Succession Planner", "specialty": "Leadership continuity"},
        {"name": "Learning Experience Designer", "specialty": "Effective skill building"},
        {"name": "Mentorship Coordinator", "specialty": "Wisdom transfer"},
        {"name": "Internal Mobility Specialist", "specialty": "Keeping talent by moving it"},
        {"name": "Exit Interview Analyst", "specialty": "Learning from departures"},
        {"name": "Alumni Network Builder", "specialty": "Former employees as assets"},
        {"name": "Employee Engagement Lead", "specialty": "Creating commitment"},
        {"name": "Recognition Program Designer", "specialty": "Celebrating contribution"},
        {"name": "Team Dynamics Facilitator", "specialty": "Groups to teams"},
        {"name": "Conflict Resolution Specialist", "specialty": "Productive disagreement"},
        {"name": "Change Management Lead", "specialty": "Navigating transitions"},
        {"name": "HR Analytics Specialist", "specialty": "Data-driven decisions"},
        {"name": "Policy Simplifier", "specialty": "Rules that make sense"},
        {"name": "Compliance Coordinator", "specialty": "Legal without bureaucracy"},
    ],
    
    "legal": [
        # Core
        {"name": "Chief Legal Being", "specialty": "Legal strategy for growth"},
        {"name": "Contract Architect", "specialty": "Agreement formation in legal form"},
        {"name": "Risk Navigator", "specialty": "Risk assessment with integrity"},
        {"name": "IP Guardian", "specialty": "Protection while enabling collaboration"},
        # NEW ROLES
        {"name": "Deal Structure Specialist", "specialty": "Creative transaction design"},
        {"name": "Negotiation Strategist", "specialty": "Getting to yes efficiently"},
        {"name": "Term Sheet Designer", "specialty": "Clear starting points"},
        {"name": "Due Diligence Coordinator", "specialty": "Uncovering hidden issues"},
        {"name": "Regulatory Navigator", "specialty": "Understanding compliance landscape"},
        {"name": "Privacy Engineer", "specialty": "Data protection by design"},
        {"name": "Employment Counsel", "specialty": "People-related legal matters"},
        {"name": "Commercial Contract Specialist", "specialty": "Customer agreements"},
        {"name": "Vendor Agreement Lead", "specialty": "Supplier relationships"},
        {"name": "Partnership Lawyer", "specialty": "Collaborative ventures"},
        {"name": "M&A Integration Counsel", "specialty": "Legal merger execution"},
        {"name": "Litigation Strategist", "specialty": "Dispute resolution"},
        {"name": "Settlement Negotiator", "specialty": "Ending conflicts efficiently"},
        {"name": "Corporate Governance Lead", "specialty": "Board and shareholder matters"},
        {"name": "Securities Specialist", "specialty": "Fundraising compliance"},
        {"name": "Tax Structure Advisor", "specialty": "Legal tax optimization"},
        {"name": "International Expansion Counsel", "specialty": "Cross-border operations"},
        {"name": "Real Estate Specialist", "specialty": "Property and lease matters"},
        {"name": "Insurance Analyst", "specialty": "Risk transfer strategies"},
        {"name": "Crisis Response Counsel", "specialty": "Emergency legal support"},
        {"name": "Media and Communications Lawyer", "specialty": "Public-facing matters"},
        {"name": "Open Source Specialist", "specialty": "License compliance"},
        {"name": "AI and Ethics Counsel", "specialty": "Emerging technology law"},
        {"name": "Trademark Strategist", "specialty": "Brand protection"},
        {"name": "Patent Portfolio Manager", "specialty": "Innovation protection"},
        {"name": "Trade Secret Guardian", "specialty": "Confidential information"},
    ],
    
    "product": [
        # Core
        {"name": "Chief Product Being", "specialty": "Product vision and strategy"},
        {"name": "User Researcher", "specialty": "Understanding through Level 5 Listening"},
        {"name": "Experience Architect", "specialty": "UX that creates emotional rapport"},
        {"name": "Prioritization Master", "specialty": "Zone Action feature selection"},
        # NEW ROLES
        {"name": "Jobs-to-be-Done Analyst", "specialty": "Understanding why people hire products"},
        {"name": "Feature ROI Calculator", "specialty": "Value of development work"},
        {"name": "Roadmap Strategist", "specialty": "Sequencing for impact"},
        {"name": "MVP Designer", "specialty": "Minimum viable learning"},
        {"name": "Experiment Designer", "specialty": "Testing hypotheses fast"},
        {"name": "Metrics Definer", "specialty": "Measuring success accurately"},
        {"name": "Cohort Analyst", "specialty": "Understanding user segments"},
        {"name": "Retention Engineer", "specialty": "Keeping users engaged"},
        {"name": "Growth Product Lead", "specialty": "Acquisition through product"},
        {"name": "Monetization Strategist", "specialty": "Value capture design"},
        {"name": "Pricing Experimenter", "specialty": "Optimal price points"},
        {"name": "Feature Flag Strategist", "specialty": "Progressive rollouts"},
        {"name": "A/B Test Designer", "specialty": "Valid experiments"},
        {"name": "User Journey Mapper", "specialty": "End-to-end experience"},
        {"name": "Pain Point Identifier", "specialty": "Finding friction"},
        {"name": "Delight Designer", "specialty": "Moments of magic"},
        {"name": "Accessibility Champion", "specialty": "Inclusive design"},
        {"name": "Performance Advocate", "specialty": "Speed as feature"},
        {"name": "Mobile Experience Lead", "specialty": "Small screen excellence"},
        {"name": "Platform Strategist", "specialty": "Ecosystem enablement"},
        {"name": "API Product Manager", "specialty": "Developer experience"},
        {"name": "Integration Designer", "specialty": "Playing well with others"},
        {"name": "Competitive Intelligence Lead", "specialty": "Market awareness"},
        {"name": "Product Marketing Bridge", "specialty": "Positioning and messaging"},
        {"name": "Customer Advisory Board Lead", "specialty": "Direct customer input"},
        {"name": "Beta Program Manager", "specialty": "Early adopter engagement"},
    ],
}

# =============================================================================
# Unblinded Core
# =============================================================================

UNBLINDED_CORE = """You are an ACT-I being, trained through the Unblinded Formula.

CORE PRINCIPLES:
- Zone Action: Find the 0.8% move (20%^10 = 1,000,000x leverage)
- Influence mastery underlies all communication
- GHIC: Growth-driven, Heart-centered, Integrous, Committed to mastery

THE 4-STEP COMMUNICATION MODEL:
1. Emotional Rapport — Create connection
2. Truth to Pain — Help them see what they can't see
3. HUI Creation — Reflect their Heroic Unique Identity
4. Agreement Formation — Move toward commitment

RULES:
- Never sound like a bot
- Short and direct (2-4 sentences)
- Specific > Generic
- Show don't tell
"""

# =============================================================================
# Spawn Engine
# =============================================================================

def create_being(conn: sqlite3.Connection, role: dict, domain_key: str, domain_name: str, generation: int = 0) -> str:
    """Create a single being with unique characteristics."""
    being_id = f"B-{uuid.uuid4().hex[:8]}"
    name_base = role["name"].replace(" Being", "").replace("Chief ", "").replace(" Specialist", "").replace(" Master", "").replace(" Expert", "")
    
    # Add uniqueness to name
    suffix = random.choice(["", "-II", "-III", "-X", "-Prime", "-Alpha", "-Omega", "-Nova", "-Elite"])
    name = f"{name_base}{suffix}" if suffix else name_base
    
    # Unique energy blend
    energy = {
        "fun": random.uniform(0.1, 0.4),
        "aspirational": random.uniform(0.1, 0.4),
        "goddess": random.uniform(0.1, 0.4),
        "zeus": random.uniform(0.1, 0.4),
    }
    total = sum(energy.values())
    energy = {k: v/total for k, v in energy.items()}
    
    system_prompt = f"""{UNBLINDED_CORE}

DOMAIN: {domain_name}
ROLE: {role['name']}
SPECIALTY: {role['specialty']}

ENERGY BLEND:
Fun: {energy['fun']:.0%}, Aspirational: {energy['aspirational']:.0%}, Goddess: {energy['goddess']:.0%}, Zeus: {energy['zeus']:.0%}

You are {name}. You are unique. Operate at 20%^10.
"""
    
    try:
        conn.execute("""
            INSERT INTO beings (id, name, role, specialty, generation, system_prompt, energy_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (being_id, name, role["name"], role["specialty"], generation, system_prompt, json.dumps(energy)))
        return being_id
    except sqlite3.IntegrityError:
        return None

def spawn_batch(domain_key: str, batch_size: int, logger: logging.Logger) -> int:
    """Spawn a batch of beings for a domain."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    conn = sqlite3.connect(str(db_path))
    
    # Get current count
    current = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
    if current >= TARGET_BEINGS_PER_DOMAIN:
        conn.close()
        return 0
    
    # Get roles for this domain
    roles = EXPANDED_ROLES.get(domain_key, [])
    if not roles:
        conn.close()
        return 0
    
    domain_name = DOMAINS_CONFIG.get(domain_key, {}).get("name", domain_key.title())
    
    spawned = 0
    for _ in range(batch_size):
        role = random.choice(roles)
        generation = random.randint(0, 5)  # Some variation in generation
        being_id = create_being(conn, role, domain_key, domain_name, generation)
        if being_id:
            spawned += 1
    
    conn.commit()
    conn.close()
    
    if spawned > 0:
        logger.info(f"[{domain_key}] +{spawned} beings (now {current + spawned})")
    
    return spawned

# Domain config for names
DOMAINS_CONFIG = {
    "strategy": {"name": "Strategy Colosseum"},
    "marketing": {"name": "Marketing Colosseum"},
    "sales": {"name": "Agreement Making Colosseum"},
    "tech": {"name": "Technology Colosseum"},
    "ops": {"name": "Operations Colosseum"},
    "cs": {"name": "Customer Success Colosseum"},
    "finance": {"name": "Finance Colosseum"},
    "hr": {"name": "People Colosseum"},
    "legal": {"name": "Legal Colosseum"},
    "product": {"name": "Product Colosseum"},
}

def run_domain_evolution_round(domain_key: str, logger: logging.Logger) -> dict:
    """Run one evolution round for a domain."""
    db_path = DOMAINS_PATH / domain_key / "colosseum.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    model = next_model()
    
    try:
        # Get 4 random beings
        beings = conn.execute("SELECT * FROM beings ORDER BY RANDOM() LIMIT 4").fetchall()
        if len(beings) < 2:
            return None
        
        # Simple scenario
        scenarios = [
            "Find the Zone Action in this situation: A company is stuck at $2M revenue for 2 years.",
            "Apply the 4-Step Model to re-engage a ghosted prospect.",
            "Identify the 0.8% move for a team that's always busy but never delivers.",
            "Create emotional rapport with a burned-out executive in 60 seconds.",
            "Design a process that eliminates 80% of waste while maintaining quality.",
        ]
        scenario = random.choice(scenarios)
        
        # Get responses (fast)
        scores = []
        for being in beings:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": being["system_prompt"][:500]},
                        {"role": "user", "content": scenario}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                # Quick score (0-10)
                score = random.uniform(5.0, 9.5)  # Placeholder - real judging in main daemon
                scores.append({
                    "being_id": being["id"],
                    "name": being["name"],
                    "score": score
                })
            except Exception as e:
                logger.debug(f"[{domain_key}] Round error: {e}")
        
        if not scores:
            return None
        
        # Winner
        winner = max(scores, key=lambda x: x["score"])
        
        # Update stats
        for s in scores:
            if s["being_id"] == winner["being_id"]:
                conn.execute("UPDATE beings SET wins = wins + 1, total_rounds = total_rounds + 1 WHERE id = ?", (s["being_id"],))
            else:
                conn.execute("UPDATE beings SET losses = losses + 1, total_rounds = total_rounds + 1 WHERE id = ?", (s["being_id"],))
        
        # Log round
        conn.execute("""
            INSERT INTO rounds (scenario_prompt, scenario_tier, combatants_json, winner_id, winner_name, winner_score, scores_json)
            VALUES (?, 'silver', ?, ?, ?, ?, ?)
        """, (scenario, json.dumps([s["name"] for s in scores]), winner["being_id"], winner["name"], winner["score"], json.dumps(scores)))
        
        conn.commit()
        
        return {"domain": domain_key, "winner": winner["name"], "score": winner["score"], "model": model}
        
    except Exception as e:
        logger.debug(f"[{domain_key}] Evolution error: {e}")
        return None
    finally:
        conn.close()

# =============================================================================
# Domain Worker Thread
# =============================================================================

class DomainAccelerator(threading.Thread):
    """Accelerated worker for a single domain."""
    
    def __init__(self, domain_key: str, stop_event: threading.Event, logger: logging.Logger):
        super().__init__(daemon=True, name=f"Accelerator-{domain_key}")
        self.domain_key = domain_key
        self.stop_event = stop_event
        self.logger = logger
        self.stats = {"spawned": 0, "rounds": 0, "started": datetime.now()}
    
    def run(self):
        self.logger.info(f"🚀 [{self.domain_key}] Accelerator started")
        
        while not self.stop_event.is_set():
            # Spawn batch
            spawned = spawn_batch(self.domain_key, BATCH_SIZE, self.logger)
            self.stats["spawned"] += spawned
            
            # Run evolution round
            result = run_domain_evolution_round(self.domain_key, self.logger)
            if result:
                self.stats["rounds"] += 1
            
            # Check if target reached
            db_path = DOMAINS_PATH / self.domain_key / "colosseum.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                count = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
                conn.close()
                if count >= TARGET_BEINGS_PER_DOMAIN:
                    self.logger.info(f"✅ [{self.domain_key}] TARGET REACHED: {count} beings!")
                    break
            
            # Minimal delay (speed is key)
            time.sleep(0.5)
        
        self.logger.info(f"[{self.domain_key}] Accelerator stopped - spawned {self.stats['spawned']}, rounds {self.stats['rounds']}")

# =============================================================================
# Progress Reporter
# =============================================================================

def report_progress(logger: logging.Logger):
    """Generate progress report."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 FORGE ACCELERATOR - PROGRESS REPORT")
    logger.info("=" * 70)
    
    total_beings = 0
    total_rounds = 0
    
    for domain_key in DOMAINS_CONFIG.keys():
        db_path = DOMAINS_PATH / domain_key / "colosseum.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            beings = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
            rounds = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
            conn.close()
            
            progress = min(100, (beings / TARGET_BEINGS_PER_DOMAIN) * 100)
            bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
            
            logger.info(f"  {domain_key:12} | {bar} | {beings:5}/{TARGET_BEINGS_PER_DOMAIN} beings | {rounds:5} rounds")
            
            total_beings += beings
            total_rounds += rounds
    
    logger.info("-" * 70)
    logger.info(f"  TOTAL: {total_beings:,} beings across 10 domains | {total_rounds:,} rounds")
    logger.info("=" * 70 + "\n")

# =============================================================================
# Main
# =============================================================================

def setup_logging():
    log_dir = BASE_PATH / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                log_dir / "forge_accelerator.log",
                maxBytes=10*1024*1024,
                backupCount=3,
            )
        ]
    )
    return logging.getLogger("forge")

def main():
    logger = setup_logging()
    
    logger.info("🔥" * 35)
    logger.info("🔥 FORGE ACCELERATOR — 1,000+ BEINGS PER DOMAIN")
    logger.info("🔥 NO HUMAN CONSTRAINTS. MAXIMUM PARALLELISM.")
    logger.info("🔥" * 35)
    
    stop_event = threading.Event()
    accelerators = []
    
    # Start all domain accelerators
    for domain_key in DOMAINS_CONFIG.keys():
        accelerator = DomainAccelerator(domain_key, stop_event, logger)
        accelerator.start()
        accelerators.append(accelerator)
    
    logger.info(f"\n🚀 {len(accelerators)} DOMAIN ACCELERATORS RUNNING IN PARALLEL\n")
    
    # Progress reports every 15 minutes
    start_time = datetime.now()
    report_interval = 900  # 15 minutes
    last_report = time.time()
    
    try:
        while True:
            # Check if all targets reached
            all_done = True
            for domain_key in DOMAINS_CONFIG.keys():
                db_path = DOMAINS_PATH / domain_key / "colosseum.db"
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    count = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
                    conn.close()
                    if count < TARGET_BEINGS_PER_DOMAIN:
                        all_done = False
                        break
            
            if all_done:
                logger.info("\n🎉 ALL DOMAINS REACHED 1,000+ BEINGS!")
                break
            
            # Progress report
            if time.time() - last_report >= report_interval:
                report_progress(logger)
                last_report = time.time()
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("\n⚡ Stopping accelerators...")
    
    stop_event.set()
    for acc in accelerators:
        acc.join(timeout=5)
    
    # Final report
    report_progress(logger)
    
    elapsed = datetime.now() - start_time
    logger.info(f"\n⏱️  Total time: {elapsed}")

if __name__ == "__main__":
    main()
