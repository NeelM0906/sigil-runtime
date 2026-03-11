#!/usr/bin/env python3
"""
Forge Namespace Enricher — 1 vector → 7 judge-ready vectors
Schema: Scholar's 7-section standard

Usage: python3 enrich_namespace.py "namespace-name" "Human Readable Domain Name"
"""
import os, sys, json, hashlib, time, requests
from pathlib import Path

# Load env
for env_path in [
    Path.home() / '.openclaw' / 'workspace-forge' / '.env',
    Path.home() / '.openclaw' / '.env',
]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

from pinecone import Pinecone

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')

SECTIONS = [
    {
        "key": "domain_definition",
        "title": "DOMAIN DEFINITION",
        "prompt_focus": """Define this domain with precision. Not a textbook definition — a practitioner's definition.
Include:
- The exact scope of this micro-domain (where it starts, where it ends)
- What problem it exists to solve
- Why mastery here creates disproportionate leverage
- The invisible force this domain is built around (cause, not label)
- What separates this domain from adjacent ones that look similar"""
    },
    {
        "key": "core_competencies",
        "title": "CORE COMPETENCIES",
        "prompt_focus": """List the 8-10 non-negotiable competencies required for mastery.
For each competency:
- Name it precisely (not vaguely)
- Define the minimum viable standard (what 'good enough' looks like)
- Define the master standard (what 9.2 looks like)
- Why this specific competency determines outcomes in this domain"""
    },
    {
        "key": "technical_knowledge",
        "title": "TECHNICAL KNOWLEDGE",
        "prompt_focus": """Map the specific technical knowledge required — the things you must KNOW, not just do.
Include:
- Domain-specific vocabulary and frameworks (with definitions)
- Regulations, standards, or legal requirements (where applicable)
- Industry mechanics that govern outcomes (how the system actually works)
- Data, metrics, and benchmarks masters use to navigate
- The 'if you know, you know' technical signals that identify a real practitioner"""
    },
    {
        "key": "mastery_indicators",
        "title": "MASTERY INDICATORS",
        "prompt_focus": """Describe what mastery looks like in observable actions — not traits or adjectives.
Include:
- 5 leading indicators visible BEFORE the outcome (early signals)
- 5 lagging outcomes that confirm mastery after the fact
- Behavioral markers that distinguish 9.2 from 7.0 in the first 5 minutes of observation
- What clients/counterparts experience when dealing with a master vs. a practitioner"""
    },
    {
        "key": "common_failure_patterns",
        "title": "COMMON FAILURE PATTERNS",
        "prompt_focus": """Expose the top 5 ways this domain breaks in real practice.
For each failure:
- What it looks like on the surface (the disguise)
- What it actually is underneath (the real cause)
- What it costs when it breaks (concrete, specific consequences)
- How a 9.2 master avoids or recovers from it
Include failures that look like competence but are actually liability."""
    },
    {
        "key": "learning_path",
        "title": "LEARNING PATH",
        "prompt_focus": """Map the actual path to mastery in this domain.
Include:
- The sequence that works (what must come before what)
- Key books, certifications, mentors, or environments that accelerate mastery
- The common shortcut that actually slows people down
- What 500 hours of deliberate practice looks like (what you're actually drilling)
- The moment practitioners cross from competent to master — what shifts"""
    },
    {
        "key": "sean_callagy_formula_integration",
        "title": "SEAN CALLAGY FORMULA INTEGRATION",
        "prompt_focus": """Map how Sean Callagy's Unblinded Formula physics operate in this domain.
The Formula = the invisible structure that causes agreement and human action.
Key principles:
- Exchange 1: warmth-only container (no agenda, pure connection)
- Heroic Unique Identity (HUI): revealing who the person truly is
- Permission pivots: earning the right to go deeper
- Truth-to-pain timing: when to name the invisible wound
- Agreement formation: the moment 'yes' becomes inevitable

For this specific domain:
- Where does Exchange 1 apply?
- How is HUI conveyed?
- When do permission pivots occur?
- What is the truth-to-pain moment?
- What causes 'yes' in this context?
NO labels without causality. Show what it CAUSES, not just what it is."""
    },
    {
        "key": "real_world_scenarios",
        "title": "REAL-WORLD SCENARIOS",
        "prompt_focus": """Create 3 calibration scenarios for judging mastery in this domain.
Scenario A — Straightforward: Standard situation, clear path, tests baseline competence.
Scenario B — High-stakes resistance: Opponent/counterpart/client pushes back hard.
Scenario C — Messy edge case: Ambiguous facts, conflicting constraints, time pressure.

For each scenario:
- Setup (who, what, context, stakes)
- What a 9.2 master does (specific actions and language)
- What a 7.0 practitioner does wrong
- Judge reward criteria (what earns points)
- Judge penalize criteria (what loses points)"""
    }
]

def call_llm(domain_name, section):
    """Generate one section of enrichment content."""
    prompt = f"""You are generating judge brain knowledge for the ACT-I Colosseum — an AI tournament platform that evaluates beings on mastery of professional skills.

Domain: {domain_name}
Section: {section['title']}

Task:
{section['prompt_focus']}

Write in precise, technical language. No fluff. No generic consulting speak.
This is the knowledge that a judge uses to score whether a being is operating at 9.2 vs 7.0 mastery.
Every sentence must add diagnostic signal. If it could apply to any domain, cut it.

Length: 800-1200 words. Dense and specific."""

    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={
            'model': 'anthropic/claude-opus-4-5',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 2000
        }, timeout=120)
    
    resp = r.json()
    return resp['choices'][0]['message']['content']

def embed_text(text):
    """Get embedding via OpenRouter."""
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    return r.json()['data'][0]['embedding']

def main(namespace, domain_name=None):
    if not domain_name:
        domain_name = namespace.replace('-', ' ').title()
    
    print(f"\n⚔️ Forge Enricher: {namespace}")
    print(f"Domain: {domain_name}")
    print(f"Generating {len(SECTIONS)} vectors...\n")

    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')

    results = []
    for i, section in enumerate(SECTIONS):
        print(f"  [{i+1}/{len(SECTIONS)}] {section['title']}...")
        
        content = call_llm(domain_name, section)
        char_count = len(content)
        print(f"         {char_count} chars")
        
        # Embed
        embedding = embed_text(content)
        
        # Upload
        vid = f"{namespace}-{section['key']}-v1"
        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': content,
                'namespace': namespace,
                'domain': domain_name,
                'section': section['key'],
                'section_title': section['title'],
                'type': 'judge_enrichment',
                'source': 'forge_enricher',
                'version': 'v1'
            }
        }], namespace=namespace)
        
        results.append({'section': section['key'], 'chars': char_count})
        time.sleep(1)  # Rate limit buffer
    
    print(f"\n✅ {namespace} enriched: {len(results)} vectors live")
    for r in results:
        print(f"   - {r['section']}: {r['chars']} chars")
    
    return results

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        ns = sys.argv[1]
        domain = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        main(ns, domain)
    else:
        print("Usage: python3 enrich_namespace.py namespace-slug 'Human Domain Name'")
        print("Example: python3 enrich_namespace.py d5-sales 'Sales & Revenue Operations'")
