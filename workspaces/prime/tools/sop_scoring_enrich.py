#!/usr/bin/env python3
"""
SOP + Scoring Metrics enrichment for acti-judges namespaces.
Adds two new vector types per namespace:
1. OPERATIONAL_SOP — step-by-step procedures, workflows, checklists
2. SCORING_METRICS — numerical thresholds per creature level

Uses Perplexity for real-world grounding + Claude for Formula integration.
"""
import os, sys, json, hashlib, time, requests, argparse
from pathlib import Path
from datetime import datetime, timezone

# Load env
env_path = Path.home() / '.openclaw' / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from pinecone import Pinecone

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')


def generate_sop(namespace):
    """Generate operational SOP for a namespace via Perplexity + Claude."""
    human_name = namespace.replace('-', ' ').title()
    
    # Step 1: Perplexity for real-world SOPs
    perplexity_prompt = f"What are the step-by-step standard operating procedures, workflows, and checklists used by top practitioners in {human_name}? Include specific tools, sequence of actions, decision points, quality gates, and handoff procedures. Focus on what a practitioner actually DOES day-to-day, not theory."
    
    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'perplexity/sonar-pro', 'messages': [{'role': 'user', 'content': perplexity_prompt}], 'max_tokens': 4000},
            timeout=60)
        web_sop = r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"  Perplexity SOP error: {e}")
        web_sop = ""
    
    time.sleep(1)
    
    # Step 2: Claude synthesizes into deployable SOP
    claude_prompt = f"""You are creating an operational SOP for an ACT-I being deployed in the role of: {human_name}

Based on this real-world research:
{web_sop[:6000]}

Create a DEPLOYABLE Standard Operating Procedure that a being can follow to execute this role. Include:

1. **DAILY WORKFLOW** — The exact sequence of actions, in order, that this role performs each day. Be specific: "Step 1: Check X. Step 2: Do Y. Step 3: If Z, then..."

2. **DECISION TREES** — The key decision points where the practitioner must choose between options. For each: the trigger, the options, the criteria for choosing, the consequence of choosing wrong.

3. **CHECKLISTS** — Pre-execution checklist (before starting work), execution checklist (during), and post-execution checklist (quality gate before delivering).

4. **TEMPLATES/SCRIPTS** — 2-3 reusable artifacts (email templates, call scripts, report frameworks) that this role uses repeatedly.

5. **HANDOFF PROTOCOLS** — How this role receives work from upstream and delivers to downstream. What information must be included. What triggers a handoff.

Be SPECIFIC. Not "communicate effectively" — rather "send a 3-paragraph status email with: context, current state, next steps, by 4pm daily."

Return dense, actionable content. Maximum 3000 words."""

    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'anthropic/claude-sonnet-4', 'messages': [{'role': 'user', 'content': claude_prompt}], 'max_tokens': 6000},
            timeout=120)
        sop_content = r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"  Claude SOP error: {e}")
        sop_content = web_sop  # Fallback to raw web research
    
    return sop_content


def generate_scoring_metrics(namespace):
    """Generate creature-level scoring metrics for a namespace."""
    human_name = namespace.replace('-', ' ').title()
    
    prompt = f"""You are creating scoring metrics for judges evaluating mastery in: {human_name}

Create SPECIFIC, NUMERICAL scoring criteria for each creature level on the Scale of Mastery:

**Grain of Sand (0.000001):** What does total incompetence look like in {human_name}? Specific observable behaviors and measurable outputs that place someone here.

**Ant (0.0001):** The person has heard of the domain but cannot execute. What specific failures indicate this level?

**Gecko (0.01):** Basic awareness, attempted execution, consistent failure. What metrics?

**Iguana (1.0):** Can follow instructions but produces mediocre output. Specific KPIs at this level.

**Komodo Dragon (100):** Common practitioner — can bump into success by accident. What separates Komodo from Iguana?

**Crocodile (10,000):** First level of intentional, reliable mastery. What SPECIFIC metrics (conversion rates, completion times, error rates, output quality scores) indicate Crocodile in this domain?

**Godzilla (1,000,000):** Industry-leading mastery. What measurable outcomes separate Godzilla from Crocodile? Be specific: "Crocodile closes 30% of qualified leads; Godzilla closes 65%+ with higher ACV."

**Bolt (9.99999):** Adding nines beyond Godzilla. What does this look like?

For EACH level, provide:
- 2-3 observable behaviors
- 1-2 measurable KPIs with actual numbers
- What a judge should look for in the being's output

The canonical creature scale: Grain of Sand → Ant → Gecko → Iguana → Komodo Dragon → Crocodile → Godzilla → Bolt Pearl
NO gorilla, lion, eagle, or any other creature. ONLY these 8 levels."""

    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'anthropic/claude-sonnet-4', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 5000},
            timeout=120)
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"  Scoring metrics error: {e}")
        return ""


def embed_text(text):
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    data = r.json()
    if 'error' in data:
        return None
    return data['data'][0]['embedding']


def upload_vectors(namespace, sop_text, scoring_text):
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')
    now = datetime.now(timezone.utc).isoformat()
    human_name = namespace.replace('-', ' ').title()
    uploaded = 0

    for section, text in [('OPERATIONAL_SOP', sop_text), ('SCORING_METRICS', scoring_text)]:
        if not text or len(text) < 100:
            continue
        
        # Chunk if needed
        chunks = []
        if len(text) > 3000:
            mid = len(text) // 2
            chunks = [text[:mid], text[mid:]]
        else:
            chunks = [text]
        
        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            if not embedding:
                continue
            
            vid = f"sop-{hashlib.md5(f'{namespace}-{section}-{i}'.encode()).hexdigest()[:12]}"
            idx.upsert(vectors=[{
                'id': vid,
                'values': embedding,
                'metadata': {
                    'text': chunk[:40000],
                    'cluster': human_name,
                    'section': section,
                    'type': 'operational' if 'SOP' in section else 'scoring',
                    'source': 'sop_scoring_enrich',
                    'uploaded_at': now,
                }
            }], namespace=namespace)
            uploaded += 1
            time.sleep(0.2)
    
    return uploaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespaces', nargs='+')
    parser.add_argument('--batch-file')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()

    if args.batch_file:
        with open(args.batch_file) as f:
            namespaces = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    elif args.namespaces:
        namespaces = args.namespaces
    elif args.all:
        pc = Pinecone(api_key=PINECONE_KEY)
        idx = pc.Index('acti-judges')
        stats = idx.describe_index_stats()
        namespaces = sorted(stats.namespaces.keys())
    else:
        parser.print_help()
        return

    total = 0
    for i, ns in enumerate(namespaces):
        print(f"[{i+1}/{len(namespaces)}] {ns}")
        
        sop = generate_sop(ns)
        print(f"  SOP: {len(sop)} chars")
        time.sleep(1)
        
        scoring = generate_scoring_metrics(ns)
        print(f"  Scoring: {len(scoring)} chars")
        time.sleep(1)

        # Save raw
        out_dir = Path.home() / '.openclaw' / 'workspace' / 'reports' / 'sop-scoring'
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{ns}-sop.md").write_text(sop)
        (out_dir / f"{ns}-scoring.md").write_text(scoring)
        
        vectors = upload_vectors(ns, sop, scoring)
        total += vectors
        print(f"  Uploaded: {vectors} vectors")
        time.sleep(2)

    print(f"\nCOMPLETE: {total} vectors across {len(namespaces)} namespaces")


if __name__ == '__main__':
    main()
