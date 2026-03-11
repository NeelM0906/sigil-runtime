#!/usr/bin/env python3
"""
Enrich acti-judges Pinecone namespaces from 1 → 8 vectors.
Follows the canonical 8-section schema:
  1. DOMAIN DEFINITION
  2. CORE COMPETENCIES
  3. TECHNICAL KNOWLEDGE
  4. MASTERY INDICATORS
  5. COMMON FAILURE PATTERNS
  6. LEARNING PATH
  7. SEAN CALLAGY FORMULA INTEGRATION
  8. REAL-WORLD SCENARIOS

Usage:
  python3 enrich_acti_judges.py "namespace-name" [--domain "Legal"] [--dry-run]
  python3 enrich_acti_judges.py --batch namespaces.txt
"""
import os, sys, json, hashlib, time, argparse, requests
from pathlib import Path
from datetime import datetime, timezone

# Load env
env_path = Path.home() / '.openclaw' / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')

SECTIONS = [
    "DOMAIN DEFINITION",
    "CORE COMPETENCIES",
    "TECHNICAL KNOWLEDGE",
    "MASTERY INDICATORS",
    "COMMON FAILURE PATTERNS",
    "LEARNING PATH",
    "SEAN CALLAGY FORMULA INTEGRATION",
    "REAL-WORLD SCENARIOS",
]

def generate_mastery_profile(namespace, domain="General"):
    """Generate a full 8-section mastery profile via Claude Opus."""
    human_name = namespace.replace('-', ' ').title()

    prompt = f"""You are creating a mastery profile for the professional skill cluster: "{human_name}" (domain: {domain}).

This profile will be used by AI judges in a Colosseum system to evaluate the mastery of AI beings competing in this skill area. The judges need DEEP, SPECIFIC, ACTIONABLE knowledge — not generic descriptions.

Create 8 sections. Each section must be 800-1500 words of DENSE, SPECIFIC content. No filler. No generic advice. Write as if you are the world's foremost expert in this exact micro-domain.

## DOMAIN DEFINITION
What this skill domain encompasses. The precise boundaries. What's in scope vs out of scope. The invisible physics of how mastery in this domain actually produces outcomes. What a layperson misunderstands about this work. The 2-3 "if you know, you know" signals that separate real practitioners from pretenders.

## CORE COMPETENCIES
8-10 specific competencies required for mastery. Not vague skills like "communication" — specific capabilities like "ability to identify the carrier's internal review threshold that triggers automatic approval vs manual review." Each competency should include what it looks like at the 7.0 (competent), 8.5 (excellent), and 9.5+ (master) level.

## TECHNICAL KNOWLEDGE
The specific tools, platforms, systems, frameworks, regulations, standards, and technical knowledge required. Include industry-specific software, methodologies, compliance requirements, and the technical foundation that separates a master from someone who just read a textbook.

## MASTERY INDICATORS
Observable behaviors and outcomes that indicate mastery. Leading indicators (what you see BEFORE results) and lagging indicators (measurable outcomes). What does a 9.0+ practitioner DO differently that you can observe? Include specific metrics, benchmarks, and behavioral markers.

## COMMON FAILURE PATTERNS
The top 7 ways practitioners fail in this domain. Not obvious failures — the SUBTLE ones that look like competence but produce mediocre outcomes. The "destroyer patterns" that masquerade as best practices. What it COSTS when each pattern goes uncorrected. Include the failure pattern, why it persists, and the specific cost.

## LEARNING PATH
The progression from novice to master. Key milestones, certifications, experiences, and deliberate practice requirements. The 5 books/resources that actually matter (not the popular ones — the ones masters actually reference). The experiences that can't be shortcut. The mentorship and feedback loops required.

## SEAN CALLAGY FORMULA INTEGRATION
How the Unblinded Formula applies to this domain:
- Exchange 1 (warmth/connection) in this context — what does the initial container look like?
- The permission pivot — how do you earn the right to go deeper?
- Truth-to-pain timing — when and how do you surface uncomfortable realities?
- The 7 Levers applied to this domain
- Zone Actions specific to this work
- Self Mastery: the internal game required (fear patterns, identity traps, emotional regulation)
- Process Mastery: the specific systems, checklists, and workflows
- No labels without causality — show the invisible causes, not just name the concepts

## REAL-WORLD SCENARIOS
5 specific test scenarios that a judge would use to evaluate mastery:
(a) Clean/straightforward scenario — tests baseline competence
(b) High-stakes scenario with resistance or pressure
(c) Messy edge case with competing priorities
(d) Ethical dilemma specific to this domain
(e) Multi-stakeholder scenario requiring influence + process mastery

For each scenario: describe the situation (3-4 sentences), state what a judge should REWARD, and what a judge should PENALIZE.

Return the content with clear ## section headers. Dense. Specific. No filler."""

    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {OPENROUTER_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': 'anthropic/claude-sonnet-4',  # Sonnet for speed on batch
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 12000,
        }, timeout=180)

    resp = r.json()
    if 'error' in resp:
        print(f"  ERROR from API: {resp['error']}")
        return None
    content = resp['choices'][0]['message']['content']
    return content


def parse_sections(content):
    """Parse the generated content into 8 sections."""
    sections = {}
    current_section = None
    current_text = []

    for line in content.split('\n'):
        # Check if this line is a section header
        stripped = line.strip().lstrip('#').strip()
        matched = None
        for s in SECTIONS:
            if s.lower() in stripped.lower():
                matched = s
                break
        if matched:
            if current_section and current_text:
                sections[current_section] = '\n'.join(current_text).strip()
            current_section = matched
            current_text = []
        elif current_section:
            current_text.append(line)

    # Don't forget the last section
    if current_section and current_text:
        sections[current_section] = '\n'.join(current_text).strip()

    return sections


def embed_text(text):
    """Get embedding via OpenRouter."""
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    data = r.json()
    if 'error' in data:
        print(f"  Embedding error: {data['error']}")
        return None
    return data['data'][0]['embedding']


def upload_to_pinecone(namespace, sections, domain, dry_run=False):
    """Upload 8 section vectors to acti-judges Pinecone."""
    if dry_run:
        print(f"  [DRY RUN] Would upload {len(sections)} vectors to {namespace}")
        for s, text in sections.items():
            print(f"    {s}: {len(text)} chars")
        return len(sections)

    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')

    uploaded = 0
    now = datetime.now(timezone.utc).isoformat()
    human_name = namespace.replace('-', ' ').title()

    for section_name, text in sections.items():
        if not text or len(text) < 50:
            print(f"  SKIP {section_name}: too short ({len(text)} chars)")
            continue

        embedding = embed_text(text)
        if not embedding:
            print(f"  SKIP {section_name}: embedding failed")
            continue

        vid = f"{namespace}-{section_name.lower().replace(' ', '-')}"
        vid = hashlib.md5(vid.encode()).hexdigest()[:16]

        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': text[:40000],
                'cluster': human_name,
                'domain': domain,
                'section': section_name,
                'type': 'mastery_research_enriched',
                'source': 'enrich_acti_judges',
                'uploaded_at': now,
            }
        }], namespace=namespace)

        uploaded += 1
        print(f"  ✅ {section_name}: {len(text)} chars → {namespace}")
        time.sleep(0.3)  # Rate limiting

    return uploaded


def enrich_namespace(namespace, domain="General", dry_run=False):
    """Full pipeline: generate → parse → embed → upload."""
    print(f"\n{'='*60}")
    print(f"Enriching: {namespace} (domain: {domain})")
    print(f"{'='*60}")

    # Generate
    print("  Generating mastery profile...")
    content = generate_mastery_profile(namespace, domain)
    if not content:
        print("  FAILED: No content generated")
        return 0

    # Save raw content
    out_dir = Path.home() / '.openclaw' / 'workspace' / 'reports' / 'acti-judges-enrichment'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{namespace}.md").write_text(content)
    print(f"  Saved raw: reports/acti-judges-enrichment/{namespace}.md ({len(content)} chars)")

    # Parse
    sections = parse_sections(content)
    print(f"  Parsed {len(sections)}/8 sections")
    if len(sections) < 6:
        print(f"  WARNING: Only {len(sections)} sections parsed. Check output.")

    # Upload
    uploaded = upload_to_pinecone(namespace, sections, domain, dry_run)
    print(f"  Result: {uploaded} vectors uploaded to {namespace}")
    return uploaded


def main():
    parser = argparse.ArgumentParser(description='Enrich acti-judges namespaces')
    parser.add_argument('namespace', nargs='?', help='Single namespace to enrich')
    parser.add_argument('--domain', default='General', help='Domain category')
    parser.add_argument('--batch', help='File with namespace:domain pairs, one per line')
    parser.add_argument('--dry-run', action='store_true', help='Generate but don\'t upload')
    args = parser.parse_args()

    if args.batch:
        with open(args.batch) as f:
            pairs = []
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(':', 1)
                ns = parts[0].strip()
                dom = parts[1].strip() if len(parts) > 1 else 'General'
                pairs.append((ns, dom))

        total = 0
        for ns, dom in pairs:
            count = enrich_namespace(ns, dom, args.dry_run)
            total += count
            time.sleep(1)  # Between namespaces

        print(f"\n{'='*60}")
        print(f"BATCH COMPLETE: {total} vectors across {len(pairs)} namespaces")
        print(f"{'='*60}")

    elif args.namespace:
        enrich_namespace(args.namespace, args.domain, args.dry_run)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
