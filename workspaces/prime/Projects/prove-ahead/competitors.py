from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List

from rich.console import Console
from rich.table import Table

from common import MATRIX_DIMENSIONS, utc_now_iso

DB_PATH = Path("data/competitors.db")

ACT_I_PROFILE = {
    "company_name": "ACT-I",
    "product": "Callie / Athena DNA",
    "category": "AI influence and conversational intelligence",
    "pricing_model": "Program-based / enterprise",
    "pricing_details": "Custom program pricing aligned to deployments and pathways",
    "capabilities": [
        "Integrity-based influence framework",
        "39-component Unblinded Formula",
        "Persistent contextual memory",
        "Multi-agent ecosystem (30 live agents)",
        "Real-time coaching and persuasion support",
        "Outcome-level interaction tracking",
    ],
    "known_customers": "100+ users with thousands of interactions",
    "funding": "Private; not publicly disclosed",
    "key_differentiators": "27-year-proven formula, 128 pathways, human-calibrated conversational strategy",
    "sources": [
        "Internal ACT-I operating metrics",
    ],
    "scores": {
        "emotional_intelligence": 5,
        "formula_based_approach": 5,
        "contextual_memory": 5,
        "multi_agent_ecosystem": 5,
        "voice_quality": 5,
        "customization_depth": 5,
        "integration_breadth": 4,
        "pricing_model": 4,
        "scale": 4,
        "results_tracking": 5,
    },
    "is_act_i": 1,
}

COMPETITOR_SEED_DATA = [
    {
        "company_name": "Bland.ai",
        "product": "Programmable AI Phone Calling API",
        "category": "Voice AI platform",
        "pricing_model": "Usage-based",
        "pricing_details": "Published per-minute pricing (e.g., around $0.09/min for base automation and $0.11/min enterprise path)",
        "capabilities": [
            "AI phone agents",
            "Programmable call flows",
            "Realtime call handling",
            "Integrations via API/webhooks",
        ],
        "known_customers": "Customer names are selectively public; broad use by sales and operations teams",
        "funding": "Series B announced June 2024 ($65M); total disclosed funding >$75M",
        "key_differentiators": "Developer-first telephony API and fast deployment model",
        "sources": [
            "https://docs.bland.ai/faq/company/pricing",
            "https://techcrunch.com/2024/06/24/bland-ai-raises-65m-to-help-enterprises-build-ai-phone-calling-agents/",
            "https://www.bland.ai/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 2,
            "voice_quality": 4,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 4,
            "scale": 4,
            "results_tracking": 2,
        },
    },
    {
        "company_name": "Air AI",
        "product": "Autonomous phone sales/support agents",
        "category": "Voice AI sales agent",
        "pricing_model": "Custom / not clearly published",
        "pricing_details": "No stable public pricing table located",
        "capabilities": [
            "Inbound and outbound voice conversations",
            "Appointment handling",
            "Sales qualification",
        ],
        "known_customers": "Customer names are mostly non-public in open sources",
        "funding": "Public startup databases list seed-stage funding; amounts vary by source",
        "key_differentiators": "Marketed as always-on autonomous phone agents",
        "sources": [
            "https://www.linkedin.com/company/air-ai1/",
            "https://www.crunchbase.com/organization/air-ai",
        ],
        "scores": {
            "emotional_intelligence": 3,
            "formula_based_approach": 1,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 2,
            "voice_quality": 4,
            "customization_depth": 3,
            "integration_breadth": 3,
            "pricing_model": 2,
            "scale": 2,
            "results_tracking": 2,
        },
    },
    {
        "company_name": "Synthflow",
        "product": "No-code AI voice agents",
        "category": "Voice AI platform",
        "pricing_model": "Subscription + usage",
        "pricing_details": "Starter published at $29/mo + usage; higher tiers and enterprise plans available",
        "capabilities": [
            "No-code voice agent builder",
            "Inbound/outbound calls",
            "CRM and tool integrations",
            "Workflow automation",
        ],
        "known_customers": "Publicly markets broad SMB and agency usage",
        "funding": "Series A announced in 2025 (publicly announced as $20M round)",
        "key_differentiators": "Fast no-code deployment with packaged voice workflows",
        "sources": [
            "https://synthflow.ai/pricing",
            "https://synthflow.ai/news/synthflow-raises-20m-series-a",
            "https://synthflow.ai/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 2,
            "voice_quality": 3,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 4,
            "scale": 3,
            "results_tracking": 2,
        },
    },
    {
        "company_name": "Vapi",
        "product": "Voice AI developer platform",
        "category": "Voice AI platform",
        "pricing_model": "Usage-based + provider costs",
        "pricing_details": "Public guidance uses per-minute platform fees plus telephony and model provider costs",
        "capabilities": [
            "Programmable voice agents",
            "API-first orchestration",
            "Realtime call tools",
            "Multimodel support",
        ],
        "known_customers": "Public site lists enterprise users and reports high call volume",
        "funding": "Seed funding publicly reported in 2024 (around $20M by Reuters)",
        "key_differentiators": "Strong developer flexibility and rapid prototyping",
        "sources": [
            "https://vapi.ai/",
            "https://support.vapi.ai/t/23483131/pricing",
            "https://www.reuters.com/world/us/voice-ai-startup-vapi-raises-20-million-us-seed-round-2024-12-12/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 3,
            "voice_quality": 4,
            "customization_depth": 5,
            "integration_breadth": 5,
            "pricing_model": 4,
            "scale": 5,
            "results_tracking": 2,
        },
    },
    {
        "company_name": "Retell AI",
        "product": "Conversational voice agents",
        "category": "Voice AI platform",
        "pricing_model": "Usage-based",
        "pricing_details": "Published per-minute pricing with optional enterprise tiers",
        "capabilities": [
            "Agentic voice conversations",
            "Call center automation",
            "Developer APIs",
            "Tool integrations",
        ],
        "known_customers": "Publicly references healthcare and services deployments",
        "funding": "Seed round publicly announced in 2024",
        "key_differentiators": "Latency and voice-interaction optimization for production calling",
        "sources": [
            "https://www.retellai.com/pricing",
            "https://www.retellai.com/blog/seed-announcement",
            "https://www.retellai.com/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 3,
            "voice_quality": 4,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 4,
            "scale": 3,
            "results_tracking": 2,
        },
    },
    {
        "company_name": "Conversica",
        "product": "Revenue Digital Assistants",
        "category": "AI sales assistant",
        "pricing_model": "Enterprise contract",
        "pricing_details": "Pricing typically quoted through sales",
        "capabilities": [
            "Lead engagement",
            "Conversation automation",
            "CRM-native workflows",
            "Revenue operations support",
        ],
        "known_customers": "Public enterprise customer stories across automotive, education, and B2B",
        "funding": "Growth-stage company; funding reported in public startup databases",
        "key_differentiators": "Longstanding AI assistant focus in sales lifecycle automation",
        "sources": [
            "https://www.conversica.com/",
            "https://www.conversica.com/customers/",
        ],
        "scores": {
            "emotional_intelligence": 3,
            "formula_based_approach": 2,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 2,
            "voice_quality": 1,
            "customization_depth": 3,
            "integration_breadth": 4,
            "pricing_model": 2,
            "scale": 4,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Drift/Salesloft",
        "product": "Conversational marketing + revenue workflow",
        "category": "Conversational marketing and sales engagement",
        "pricing_model": "Enterprise SaaS",
        "pricing_details": "Tiered contracts with sales-led pricing",
        "capabilities": [
            "Website conversational experiences",
            "Buyer engagement",
            "Meeting routing",
            "Revenue workflow integrations",
        ],
        "known_customers": "Large B2B customer base via Salesloft and legacy Drift accounts",
        "funding": "Private company; major PE-backed rounds and acquisition activity",
        "key_differentiators": "Strong GTM workflow coverage and enterprise sales orchestration",
        "sources": [
            "https://www.salesloft.com/company/news/salesloft-announces-acquisition-of-drift",
            "https://www.salesloft.com/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 2,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 2,
            "voice_quality": 1,
            "customization_depth": 3,
            "integration_breadth": 5,
            "pricing_model": 2,
            "scale": 5,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Gong",
        "product": "Revenue intelligence platform",
        "category": "Conversation intelligence",
        "pricing_model": "Seat-based enterprise SaaS",
        "pricing_details": "Quoted plans via sales",
        "capabilities": [
            "Call recording and analysis",
            "Deal intelligence",
            "Coaching analytics",
            "Forecasting insights",
        ],
        "known_customers": "Large enterprise roster across SaaS, finance, and services",
        "funding": "Series E announced at $250M (public press release)",
        "key_differentiators": "Deep conversation analytics and pipeline intelligence",
        "sources": [
            "https://www.gong.io/press/gong-raises-250-million-in-series-e-funding-at-7-25-billion-valuation/",
            "https://www.gong.io/customers/",
            "https://www.gong.io/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 2,
            "voice_quality": 1,
            "customization_depth": 3,
            "integration_breadth": 5,
            "pricing_model": 2,
            "scale": 5,
            "results_tracking": 5,
        },
    },
    {
        "company_name": "Outreach",
        "product": "Sales execution platform",
        "category": "Sales engagement",
        "pricing_model": "Seat-based enterprise SaaS",
        "pricing_details": "Plans are quoted via sales",
        "capabilities": [
            "Sequencing and cadences",
            "Conversation workflows",
            "Forecast and pipeline support",
            "CRM integration",
        ],
        "known_customers": "Large global sales teams and mid-market SaaS customers",
        "funding": "Publicly announced $200M financing round in 2021",
        "key_differentiators": "Large installed base and mature sales process automation",
        "sources": [
            "https://www.prnewswire.com/news-releases/outreach-closes-200-million-round-4-4-billion-valuation-for-sales-engagement-category-leader-301304239.html",
            "https://www.outreach.io/customers",
            "https://www.outreach.io/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 2,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 2,
            "voice_quality": 1,
            "customization_depth": 4,
            "integration_breadth": 5,
            "pricing_model": 2,
            "scale": 5,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Ada",
        "product": "AI customer service automation",
        "category": "Customer service AI",
        "pricing_model": "Enterprise SaaS",
        "pricing_details": "Public pricing starts at enterprise tiers, quote-led",
        "capabilities": [
            "AI support automation",
            "Knowledge-grounded responses",
            "Omnichannel service",
            "Agent handoff",
        ],
        "known_customers": "Public customer stories include enterprises in retail, fintech, and travel",
        "funding": "Growth-stage company with publicly reported venture rounds",
        "key_differentiators": "Customer-service-first AI operating model",
        "sources": [
            "https://www.ada.cx/pricing",
            "https://www.ada.cx/customers",
            "https://www.ada.cx/",
        ],
        "scores": {
            "emotional_intelligence": 3,
            "formula_based_approach": 1,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 3,
            "voice_quality": 2,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 2,
            "scale": 5,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Intercom Fin",
        "product": "Fin AI Agent",
        "category": "Customer support AI",
        "pricing_model": "Hybrid (per-resolution + platform)",
        "pricing_details": "Public pricing includes usage-based Fin metrics with platform plans",
        "capabilities": [
            "AI support agent",
            "Knowledge integration",
            "Workflow automation",
            "Human handoff",
        ],
        "known_customers": "Public customer stories include SaaS and ecommerce operators",
        "funding": "Late-stage private company with multiple public rounds",
        "key_differentiators": "Tight integration with Intercom support stack",
        "sources": [
            "https://www.intercom.com/fin/pricing",
            "https://www.intercom.com/customers",
            "https://www.intercom.com/",
        ],
        "scores": {
            "emotional_intelligence": 3,
            "formula_based_approach": 1,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 4,
            "voice_quality": 1,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 3,
            "scale": 5,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "PolyAI",
        "product": "Enterprise voice assistants",
        "category": "Enterprise voice AI",
        "pricing_model": "Enterprise contract",
        "pricing_details": "Custom pricing for enterprise deployments",
        "capabilities": [
            "Natural voice assistants",
            "Call center automation",
            "Multilingual support",
            "Enterprise integrations",
        ],
        "known_customers": "Public references include FedEx, Marriott, Caesars, and Unicredit",
        "funding": "$86M funding round announced in 2024",
        "key_differentiators": "Enterprise-grade voice assistant quality and support footprint",
        "sources": [
            "https://poly.ai/blog/polyai-raises-86m-to-transform-how-enterprises-talk-to-their-customers/",
            "https://poly.ai/",
        ],
        "scores": {
            "emotional_intelligence": 3,
            "formula_based_approach": 1,
            "contextual_memory": 4,
            "multi_agent_ecosystem": 3,
            "voice_quality": 5,
            "customization_depth": 4,
            "integration_breadth": 4,
            "pricing_model": 2,
            "scale": 4,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Talkdesk",
        "product": "Cloud contact center + AI",
        "category": "Contact center AI",
        "pricing_model": "Per-seat SaaS + add-ons",
        "pricing_details": "Public plans are tiered per-seat with AI add-on packaging",
        "capabilities": [
            "AI customer experience automation",
            "Voice and digital channels",
            "Workforce orchestration",
            "Enterprise analytics",
        ],
        "known_customers": "Public enterprise customer references across retail, healthcare, and finance",
        "funding": "Late-stage private company; funding >$400M publicly reported",
        "key_differentiators": "End-to-end contact center suite with embedded AI",
        "sources": [
            "https://www.talkdesk.com/contact-center-software/pricing/",
            "https://www.talkdesk.com/customers/",
            "https://www.fool.com/investing/2021/10/07/talkdesk-joins-list-of-new-unicorns-with-10b-valu/",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 4,
            "voice_quality": 4,
            "customization_depth": 4,
            "integration_breadth": 5,
            "pricing_model": 3,
            "scale": 5,
            "results_tracking": 4,
        },
    },
    {
        "company_name": "Five9",
        "product": "Intelligent CX platform",
        "category": "Contact center + conversational AI",
        "pricing_model": "Enterprise subscription",
        "pricing_details": "Quote-led enterprise pricing",
        "capabilities": [
            "Voice and digital contact center",
            "AI-driven routing",
            "Automation workflows",
            "Analytics and reporting",
        ],
        "known_customers": "Large contact center customer base in regulated and enterprise sectors",
        "funding": "Public company (NASDAQ: FIVN)",
        "key_differentiators": "Contact-center depth and enterprise-grade reliability",
        "sources": [
            "https://www.five9.com/",
            "https://www.five9.com/customers",
            "https://www.five9.com/company/investor-relations",
        ],
        "scores": {
            "emotional_intelligence": 2,
            "formula_based_approach": 1,
            "contextual_memory": 3,
            "multi_agent_ecosystem": 3,
            "voice_quality": 4,
            "customization_depth": 4,
            "integration_breadth": 5,
            "pricing_model": 2,
            "scale": 5,
            "results_tracking": 4,
        },
    },
]


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE,
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            pricing_model TEXT NOT NULL,
            pricing_details TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            known_customers TEXT NOT NULL,
            funding TEXT NOT NULL,
            key_differentiators TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            scores_json TEXT NOT NULL,
            is_act_i INTEGER NOT NULL DEFAULT 0,
            last_verified_utc TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _serialize_list(values: Iterable[str]) -> str:
    return json.dumps(list(values), ensure_ascii=True)


def _serialize_dict(values: Dict[str, int]) -> str:
    clean = {k: int(values[k]) for k in MATRIX_DIMENSIONS}
    return json.dumps(clean, ensure_ascii=True)


def seed_competitors(conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    all_records = [ACT_I_PROFILE] + COMPETITOR_SEED_DATA

    for record in all_records:
        conn.execute(
            """
            INSERT INTO competitors (
                company_name,
                product,
                category,
                pricing_model,
                pricing_details,
                capabilities_json,
                known_customers,
                funding,
                key_differentiators,
                sources_json,
                scores_json,
                is_act_i,
                last_verified_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_name) DO UPDATE SET
                product=excluded.product,
                category=excluded.category,
                pricing_model=excluded.pricing_model,
                pricing_details=excluded.pricing_details,
                capabilities_json=excluded.capabilities_json,
                known_customers=excluded.known_customers,
                funding=excluded.funding,
                key_differentiators=excluded.key_differentiators,
                sources_json=excluded.sources_json,
                scores_json=excluded.scores_json,
                is_act_i=excluded.is_act_i,
                last_verified_utc=excluded.last_verified_utc
            """,
            (
                record["company_name"],
                record["product"],
                record["category"],
                record["pricing_model"],
                record["pricing_details"],
                _serialize_list(record["capabilities"]),
                record["known_customers"],
                record["funding"],
                record["key_differentiators"],
                _serialize_list(record["sources"]),
                _serialize_dict(record["scores"]),
                record.get("is_act_i", 0),
                now,
            ),
        )
    conn.commit()


def load_competitors(conn: sqlite3.Connection, include_act_i: bool = False) -> List[Dict[str, object]]:
    query = "SELECT * FROM competitors"
    params: List[object] = []
    if not include_act_i:
        query += " WHERE is_act_i = 0"
    query += " ORDER BY company_name ASC"

    rows = conn.execute(query, params).fetchall()
    result: List[Dict[str, object]] = []
    for row in rows:
        result.append(
            {
                "company_name": row["company_name"],
                "product": row["product"],
                "category": row["category"],
                "pricing_model": row["pricing_model"],
                "pricing_details": row["pricing_details"],
                "capabilities": json.loads(row["capabilities_json"]),
                "known_customers": row["known_customers"],
                "funding": row["funding"],
                "key_differentiators": row["key_differentiators"],
                "sources": json.loads(row["sources_json"]),
                "scores": json.loads(row["scores_json"]),
                "is_act_i": bool(row["is_act_i"]),
                "last_verified_utc": row["last_verified_utc"],
            }
        )
    return result


def get_act_i_profile(conn: sqlite3.Connection) -> Dict[str, object]:
    row = conn.execute("SELECT * FROM competitors WHERE is_act_i = 1 LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("ACT-I profile missing; run competitors.py --seed first")
    return {
        "company_name": row["company_name"],
        "product": row["product"],
        "category": row["category"],
        "pricing_model": row["pricing_model"],
        "pricing_details": row["pricing_details"],
        "capabilities": json.loads(row["capabilities_json"]),
        "known_customers": row["known_customers"],
        "funding": row["funding"],
        "key_differentiators": row["key_differentiators"],
        "sources": json.loads(row["sources_json"]),
        "scores": json.loads(row["scores_json"]),
        "is_act_i": True,
        "last_verified_utc": row["last_verified_utc"],
    }


def init_and_seed(db_path: Path = DB_PATH) -> None:
    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        seed_competitors(conn)
    finally:
        conn.close()


def show_registry(db_path: Path = DB_PATH) -> None:
    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        rows = load_competitors(conn, include_act_i=True)
    finally:
        conn.close()

    console = Console()
    table = Table(title=f"Competitor Registry ({len(rows)} records)")
    table.add_column("Company", style="bold")
    table.add_column("Product")
    table.add_column("Category")
    table.add_column("Pricing")
    table.add_column("Funding")

    for row in rows:
        table.add_row(
            row["company_name"],
            row["product"],
            row["category"],
            row["pricing_model"],
            row["funding"],
        )

    console.print(table)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and inspect the competitor registry")
    parser.add_argument("--seed", action="store_true", help="Create/update the SQLite registry")
    parser.add_argument("--show", action="store_true", help="Show current registry in Rich table format")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)

    if args.seed:
        init_and_seed(db_path)

    if args.show:
        show_registry(db_path)

    if not args.seed and not args.show:
        init_and_seed(db_path)
        show_registry(db_path)


if __name__ == "__main__":
    main()
