#!/usr/bin/env python3
"""
ACT-I Mastery Database Builder
Researches mastery knowledge for each cluster/position
Outputs structured data for Pinecone upload and Google Sheets

Usage: python3 mastery_researcher.py --cluster "Hunter" --limit 5
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
WORKSPACE = Path("~/.openclaw/workspace-forge")
OUTPUT_DIR = WORKSPACE / "reports" / "mastery-database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-sonnet-4-6"

# ── Cluster Registry (from Aiko's screenshots) ──────────────────────────────
CLUSTERS = {
    "Social": {"domain": "Social Media Management", "positions": 189, "lever": "0.5, 2", "family": "The Voice"},
    "Oracle": {"domain": "Data Analytics & Intelligence", "positions": 169, "lever": "2, Analytics", "family": "The Analyst"},
    "StageHand": {"domain": "Event Production & Logistics", "positions": 144, "lever": "0.5, 2", "family": "The Stage Director"},
    "Hunter": {"domain": "Outreach & Lead Development", "positions": 86, "lever": "0.5, 3", "family": "The Agreement Maker"},
    "Canvas": {"domain": "Visual & Graphic Design", "positions": 82, "lever": "2", "family": "The Visual Architect"},
    "ValueEngine": {"domain": "Customer Economics & LTV Analytics", "positions": 74, "lever": "5", "family": "The Analyst"},
    "PriceArchitect": {"domain": "Pricing & Revenue Strategy", "positions": 62, "lever": "4", "family": "The Operator"},
    "Healer": {"domain": "Social Impact & CSR", "positions": 60, "lever": "6", "family": "The Multiplier"},
    "Sage": {"domain": "Thought Leadership & Influence", "positions": 60, "lever": "6", "family": "The Multiplier"},
    "Enchanter": {"domain": "Experience Design & Delight", "positions": 59, "lever": "7", "family": "The Strategist"},
    "Guardian": {"domain": "Customer Success & Account Growth", "positions": 54, "lever": "3, 4", "family": "The Keeper"},
    "SoundForge": {"domain": "Audio Engineering & Sound Design", "positions": 52, "lever": "2", "family": "The Sound Engineer"},
    "Scout": {"domain": "Partnership Research & Intelligence", "positions": 50, "lever": "1", "family": "The Analyst"},
    "Virtual": {"domain": "Webinar & Virtual Events", "positions": 49, "lever": "0.5, 2", "family": "The Stage Director"},
    "Architect": {"domain": "Content Strategy & Management", "positions": 49, "lever": "2", "family": "The Writer"},
    "Treasurer": {"domain": "Financial Planning & Analysis", "positions": 48, "lever": "5", "family": "The Operator"},
    "AgreementMaker": {"domain": "Agreement Making", "positions": 47, "lever": "3", "family": "The Agreement Maker"},
    "MediaBuyer": {"domain": "Paid Media & Ad Ops", "positions": 46, "lever": "2", "family": "The Media Buyer"},
    "Integrator": {"domain": "Partnership Integration & Ops", "positions": 46, "lever": "1", "family": "The Connector"},
    "RevInsight": {"domain": "Revenue Analytics", "positions": 42, "lever": "4", "family": "The Analyst"},
    "Director": {"domain": "Video Direction & Production", "positions": 41, "lever": "0.5, 2", "family": "The Filmmaker"},
    "Bridge": {"domain": "Partnership Development", "positions": 40, "lever": "1", "family": "The Connector"},
    "Distributor": {"domain": "Video Operations & Distribution", "positions": 39, "lever": "2", "family": "The Filmmaker"},
    "AudioReach": {"domain": "Audio Marketing & Distribution", "positions": 39, "lever": "2", "family": "The Sound Engineer"},
    "Enabler": {"domain": "Revenue Operations & Enablement", "positions": 38, "lever": "3", "family": "The Agreement Maker"},
    "AdSmith": {"domain": "Ad Creative Production", "positions": 33, "lever": "2", "family": "The Filmmaker"},
    "Podcast": {"domain": "Podcast & Audio Production", "positions": 33, "lever": "0.5, 2", "family": "The Sound Engineer"},
    "GripMaster": {"domain": "Production Operations & Logistics", "positions": 27, "lever": "2", "family": "The Stage Director"},
    "Scholar-Scribe": {"domain": "PR & Media Relations", "positions": 27, "lever": "2", "family": "The Writer"},
    "Sphinx": {"domain": "Interactive & Quiz Design", "positions": 27, "lever": "0.5, 2", "family": "The Visual Architect"},
    "Rigger": {"domain": "Stage & Technical Production", "positions": 26, "lever": "2", "family": "The Stage Director"},
    "Promoter": {"domain": "Event Marketing & Promotion", "positions": 25, "lever": "2", "family": "The Voice"},
    "Interface": {"domain": "UX & Interface Writing", "positions": 24, "lever": "2", "family": "The Writer"},
    "Automator": {"domain": "Email & SMS Marketing Automation", "positions": 23, "lever": "2", "family": "The Technologist"},
    "Scribe": {"domain": "SEO & Content Writing", "positions": 23, "lever": "2", "family": "The Writer"},
    "ChannelMaster": {"domain": "Platform & Channel Partnerships", "positions": 22, "lever": "1", "family": "The Media Buyer"},
    "Steward": {"domain": "Community Management", "positions": 22, "lever": "0.5, 2", "family": "The Multiplier"},
    "Illustra": {"domain": "Illustration & Fine Art", "positions": 22, "lever": "2", "family": "The Visual Architect"},
    "Bard": {"domain": "Narrative & Long-Form Writing", "positions": 22, "lever": "2", "family": "The Writer"},
    "Curator": {"domain": "Event Strategy & Curation", "positions": 21, "lever": "2", "family": "The Stage Director"},
    "Optimizer": {"domain": "Conversion Rate Optimization", "positions": 21, "lever": "2, Analytics", "family": "The Operator"},
    "Cultivator": {"domain": "Partnership Nurturing & Relationships", "positions": 21, "lever": "1", "family": "The Connector"},
    "Lens": {"domain": "Cinematography & Lighting", "positions": 18, "lever": "2", "family": "The Filmmaker"},
    "Editor": {"domain": "Video Post-Production & VFX", "positions": 18, "lever": "2", "family": "The Filmmaker"},
    "Orator": {"domain": "Speaker Development & Coaching", "positions": 18, "lever": "2", "family": "The Voice"},
    "RevOps": {"domain": "Revenue Operations", "positions": 18, "lever": "4", "family": "The Operator"},
    "Flow": {"domain": "UX/UI Design", "positions": 18, "lever": "2", "family": "The Writer"},
    "Neuron": {"domain": "Data Science & Engineering", "positions": 17, "lever": "Analytics", "family": "The Analyst"},
    "BookAgent": {"domain": "Speaking & Stage Ops", "positions": 17, "lever": "2", "family": "The Stage Director"},
    "Shield": {"domain": "Legal & Compliance", "positions": 17, "lever": "1", "family": "The Researcher"},
    "Identity": {"domain": "Brand Strategy & Messaging", "positions": 17, "lever": "2", "family": "The Visual Architect"},
    "Pixel": {"domain": "Digital & Web Design", "positions": 17, "lever": "2", "family": "The Visual Architect"},
    "Voice": {"domain": "Voice Performance & Presenting", "positions": 16, "lever": "2", "family": "The Voice"},
    "Clarity": {"domain": "Data Visualization & Dashboards", "positions": 16, "lever": "2, Analytics", "family": "The Visual Architect"},
    "Builder": {"domain": "Web Development & Technology", "positions": 14, "lever": "2", "family": "The Technologist"},
    "Environ": {"domain": "Environmental & Spatial Design", "positions": 14, "lever": "2", "family": "The Visual Architect"},
    "Persuader": {"domain": "Conversion Copywriting", "positions": 14, "lever": "2", "family": "The Writer"},
    "Dealmaker": {"domain": "Partnership Agreement Making", "positions": 13, "lever": "1", "family": "The Connector"},
    "SetMaster": {"domain": "Production Design & Art Direction", "positions": 13, "lever": "2", "family": "The Visual Architect"},
    "CoCreator": {"domain": "Partnership Marketing & Content", "positions": 13, "lever": "1", "family": "The Connector"},
    "Visionary": {"domain": "Creative Direction & Design Ops", "positions": 11, "lever": "2", "family": "The Visual Architect"},
    "Broadcaster": {"domain": "Content Distribution & Promotion", "positions": 11, "lever": "2", "family": "The Voice"},
    "Spider": {"domain": "SEO Technical", "positions": 10, "lever": "2", "family": "The Technologist"},
    "Discoverer": {"domain": "Partnership Sourcing & Outreach", "positions": 10, "lever": "1", "family": "The Researcher"},
    "Kinetic": {"domain": "Motion Graphics & Animation", "positions": 10, "lever": "2", "family": "The Visual Architect"},
    "Coach": {"domain": "Revenue Training & Coaching", "positions": 8, "lever": "3", "family": "The Agreement Maker"},
    "Playwright": {"domain": "Script & Speech Writing", "positions": 8, "lever": "2", "family": "The Writer"},
    "TouchPoint": {"domain": "Physical Touch & Direct Mail", "positions": 7, "lever": "0.5", "family": "The Messenger"},
    "Form": {"domain": "Product & Industrial Design", "positions": 7, "lever": "2", "family": "The Visual Architect"},
    "Genesis": {"domain": "ACT-I Being Development", "positions": 6, "lever": "Other", "family": "The Strategist"},
    "Pipeline": {"domain": "CRM & Marketing Automation", "positions": 5, "lever": "2, Analytics", "family": "The Analyst"},
    "Nurture": {"domain": "Email & Nurture Copywriting", "positions": 5, "lever": "2", "family": "The Messenger"},
    "Inspector": {"domain": "Quality Assurance & Testing", "positions": 4, "lever": "2", "family": "The Keeper"},
    "OpsEngine": {"domain": "Marketing Operations", "positions": 4, "lever": "2", "family": "The Operator"},
    "Shutter": {"domain": "Photography", "positions": 3, "lever": "2", "family": "The Filmmaker"},
    "Herald": {"domain": "PR & Brand Copywriting", "positions": 3, "lever": "2", "family": "The Messenger"},
    "Pulse": {"domain": "Social Media Copywriting", "positions": 3, "lever": "2", "family": "The Messenger"},
    "Conductor": {"domain": "Project Management", "positions": 2, "lever": "Analytics", "family": "The Operator"},
    "Translator": {"domain": "Localization & Translation", "positions": 2, "lever": "Other", "family": "The Operator"},
}


def call_openrouter(prompt: str, system: str = "") -> str:
    """Call OpenRouter API with Claude Sonnet."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://acti.ai",
            "X-Title": "ACT-I Mastery Database Builder"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
        return data["choices"][0]["message"]["content"]


def research_cluster(cluster_name: str, cluster_info: dict) -> dict:
    """Research mastery knowledge for a cluster."""
    domain = cluster_info["domain"]
    family = cluster_info["family"]

    system = """You are a world-class domain knowledge synthesizer. 
Your job: produce the definitive mastery profile for a professional role.
Be specific, practical, and comprehensive. No filler. Every sentence must be learnable."""

    prompt = f"""Research and synthesize the complete mastery profile for the "{cluster_name}" cluster — {domain}.

Produce a structured profile with exactly these 8 sections:

1. DOMAIN DEFINITION (2-3 sentences: what this role does, why it matters)

2. CORE COMPETENCIES (8-10 specific skills — what a master practitioner can do that a novice cannot)

3. TECHNICAL KNOWLEDGE (specific tools, platforms, frameworks, methodologies that masters use — name them explicitly: e.g., "GA4 custom dimensions", not "analytics tools")

4. MASTERY INDICATORS (what does 9.0/10.0 performance look like in this domain? 3-5 specific, observable outcomes)

5. COMMON FAILURE PATTERNS (top 3 mistakes practitioners make at 6.0-7.0 skill level that prevent reaching mastery)

6. LEARNING PATH (what someone must learn, in order, to go from novice → proficient → master — specific resources, concepts, milestones)

7. SEAN CALLAGY FORMULA INTEGRATION (how does this role connect to the 4 Steps of Communication: Emotional Rapport, Truth to Pain, Heroic Unique Identity, Agreement Formation? Which levers apply: {cluster_info["lever"]}?)

8. REAL-WORLD SCENARIOS (3 specific scenarios this role would face — one at novice level, one at proficient, one at master level — showing the behavioral difference)

Format as clean text. Each section header on its own line. Be specific enough that someone could use this to build an AI being or train a human practitioner."""

    result = call_openrouter(prompt, system)
    
    return {
        "cluster": cluster_name,
        "domain": domain,
        "family": family,
        "positions": cluster_info["positions"],
        "lever": cluster_info["lever"],
        "mastery_profile": result,
        "researched_at": datetime.now().isoformat(),
        "model": MODEL,
        # Pinecone-ready format
        "pinecone_text": f"CLUSTER: {cluster_name}\nDOMAIN: {domain}\nFAMILY: {family}\n\n{result}",
        "metadata": {
            "cluster": cluster_name,
            "domain": domain,
            "family": family,
            "positions": cluster_info["positions"],
            "lever": cluster_info["lever"],
            "source": "mastery_researcher_v1",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    }


def to_sheet_row(profile: dict) -> list:
    """Convert profile to Google Sheets row format."""
    return [
        profile["cluster"],
        profile["domain"],
        profile["family"],
        str(profile["positions"]),
        profile["lever"],
        profile["mastery_profile"],
        profile["researched_at"]
    ]


def save_profile(profile: dict):
    """Save profile to disk."""
    cluster = profile["cluster"]
    filepath = OUTPUT_DIR / f"{cluster.lower()}-mastery.json"
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)
    
    # Also save plain text for easy reading
    txt_path = OUTPUT_DIR / f"{cluster.lower()}-mastery.md"
    with open(txt_path, "w") as f:
        f.write(f"# {cluster} — {profile['domain']}\n")
        f.write(f"**Family:** {profile['family']} | **Positions:** {profile['positions']} | **Lever:** {profile['lever']}\n\n")
        f.write(profile["mastery_profile"])
    
    print(f"✅ Saved: {cluster} → {filepath.name}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="ACT-I Mastery Database Builder")
    parser.add_argument("--cluster", help="Single cluster to research")
    parser.add_argument("--family", help="Research all clusters in a family")
    parser.add_argument("--limit", type=int, default=5, help="Max clusters to research")
    parser.add_argument("--all", action="store_true", help="Research all clusters")
    parser.add_argument("--sheet-headers", action="store_true", help="Print sheet headers only")
    args = parser.parse_args()

    if args.sheet_headers:
        headers = ["Cluster", "Domain", "Family", "Positions", "Lever", "Mastery Profile", "Researched At"]
        print(json.dumps(headers))
        return

    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    clusters_to_research = []
    
    if args.cluster:
        if args.cluster in CLUSTERS:
            clusters_to_research = [(args.cluster, CLUSTERS[args.cluster])]
        else:
            print(f"Unknown cluster: {args.cluster}")
            print(f"Available: {', '.join(CLUSTERS.keys())}")
            sys.exit(1)
    elif args.family:
        clusters_to_research = [
            (name, info) for name, info in CLUSTERS.items() 
            if info["family"] == args.family
        ]
    elif args.all:
        clusters_to_research = list(CLUSTERS.items())
    else:
        # Default: top clusters by position count
        clusters_to_research = sorted(
            CLUSTERS.items(), 
            key=lambda x: x[1]["positions"], 
            reverse=True
        )[:args.limit]

    print(f"🔬 Researching {len(clusters_to_research)} clusters...")
    
    all_rows = []
    for cluster_name, cluster_info in clusters_to_research:
        print(f"\n⚔️  Researching: {cluster_name} — {cluster_info['domain']}")
        try:
            profile = research_cluster(cluster_name, cluster_info)
            save_profile(profile)
            all_rows.append(to_sheet_row(profile))
            print(f"   {len(profile['mastery_profile'])} chars generated")
            time.sleep(2)  # Rate limit courtesy
        except Exception as e:
            print(f"   ERROR: {e}")
            continue

    # Save consolidated output
    consolidated_path = OUTPUT_DIR / "all-mastery-rows.json"
    with open(consolidated_path, "w") as f:
        json.dump({
            "headers": ["Cluster", "Domain", "Family", "Positions", "Lever", "Mastery Profile", "Researched At"],
            "rows": all_rows,
            "total": len(all_rows),
            "generated_at": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n✅ Complete. {len(all_rows)} clusters researched.")
    print(f"📄 Consolidated: {consolidated_path}")
    print(f"📂 Individual files: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()


def save_to_supabase(profile: dict):
    """Write mastery profile to Supabase shared brain."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from supabase_memory import SaiMemory
        mem = SaiMemory("forge")
        
        content = (
            f"CLUSTER: {profile['cluster']}\n"
            f"DOMAIN: {profile['domain']}\n"
            f"FAMILY: {profile['family']}\n"
            f"POSITIONS: {profile['positions']}\n"
            f"LEVER: {profile['lever']}\n\n"
            f"{profile['mastery_profile']}"
        )
        
        mem.remember(
            category="mastery_research",
            content=content,
            source=f"mastery_researcher_v1:{profile['cluster']}",
            importance=8
        )
        print(f"   → Supabase: {profile['cluster']} written")
        return True
    except Exception as e:
        print(f"   → Supabase write failed: {e}")
        return False
