#!/usr/bin/env python3
"""
Self Mastery Calibration Miner — Phase 1 of Formula Judge Grounding

Mines ublib2 (58K vectors) and ultimatestratabrain (39K vectors) for concrete
creature-level anchors for each Self Mastery dimension.

Goal: Extract what Sean ACTUALLY said a 4.0 vs 7.0 vs 9.0 looks like —
from real coaching sessions, real moments, real interventions.

Output: reports/self-mastery-calibration-anchors.md
"""

import os
import sys
import json
import time
import requests
from pinecone import Pinecone

# Config
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_API_KEY_STRATA = os.environ.get('PINECONE_API_KEY_STRATA')

# Self Mastery dimensions to mine (12 components from Kai's blueprint)
SELF_MASTERY_DIMENSIONS = [
    {
        "id": "SM-1",
        "name": "Physiology Management",
        "queries": [
            "physiology determines mindset state management body posture energy",
            "physical state coaching session Sean teaching body breath energy level",
            "physiology destroyer self mastery what happens when depleted exhausted",
            "scoring physiology mastery change your state change your body"
        ]
    },
    {
        "id": "SM-2", 
        "name": "Driving Why (Depth & Emotional Fuel)",
        "queries": [
            "driving why emotional fuel purpose strong why vs weak why coaching",
            "why that makes you cry shivers body deeper purpose driving force",
            "weak why collapses first resistance shallow motivation vs deep",
            "scoring why mastery depth of purpose coaching example"
        ]
    },
    {
        "id": "SM-3",
        "name": "Identity Selection (Heroic Relevant Identities)",
        "queries": [
            "identity selection heroic relevant choosing who you are being",
            "identity shapes beliefs actions results you are who you decide to be",
            "identity destroyer not choosing empowering identities coaching",
            "GHIC growth driven heart centered integrous committed identity"
        ]
    },
    {
        "id": "SM-4",
        "name": "Beliefs (Limiting vs Empowering)",
        "queries": [
            "limiting beliefs empowering beliefs replace what you believe accelerate destroy",
            "beliefs scoring mastery coaching session identifying replacing beliefs",
            "fear disguised as limiting belief perfectionism hiding readiness",
            "beliefs destroyer not choosing relevant limiting empowering beliefs"
        ]
    },
    {
        "id": "SM-5",
        "name": "Fear of Rejection (Navigation)",
        "queries": [
            "fear of rejection belief rejection exists avoidance negative attention",
            "rejection doesn't exist unblinded position speaking into fear",
            "fear of rejection coaching session overcoming avoiding confrontation",
            "destroyer five fear rejection mastery scoring breakthrough"
        ]
    },
    {
        "id": "SM-5.5",
        "name": "Avoidance (The Behavioral Mechanism)",
        "queries": [
            "avoidance dressed as preparation fear masked as strategy patience",
            "avoidance mechanism destroyers five through seven behavioral pattern",
            "avoidance disguised as professionalism respect following instructions",
            "organizational fear avoidance coaching session identifying"
        ]
    },
    {
        "id": "SM-6",
        "name": "Fear of Failure / Perfectionism",
        "queries": [
            "fear failure perfectionism I'm not ready yet masquerades high standards",
            "perfectionism hiding behind strategic patience coaching session",
            "fixed mindset growth mindset fear failure destroyer six",
            "scoring fear failure mastery overcoming perfectionism coaching"
        ]
    },
    {
        "id": "SM-7",
        "name": "Zone Action Certainty",
        "queries": [
            "zone action certainty knowing vital few moves 0.16% activity",
            "lack certainty zone action distraction scattered activity unfocused",
            "zone action identification scoring what separates mastery coaching",
            "destroyer seven certainty zone action discipline focus coaching"
        ]
    },
    {
        "id": "SM-8",
        "name": "6 Human Needs Awareness & Hierarchy",
        "queries": [
            "six human needs certainty variety significance connection growth contribution",
            "optimal hierarchy growth contribution first significance last coaching",
            "significance driven certainty driven prevents confrontation risk",
            "human needs awareness coaching session scoring mastery"
        ]
    },
    {
        "id": "SM-9",
        "name": "Focus & Meaning-Making",
        "queries": [
            "focus meaning making what you focus on determines quality of life",
            "focus direction determines reality meaning interpretation coaching",
            "emotional triad physiology focus language meaning self mastery",
            "focus mastery coaching scoring what separates high performers"
        ]
    },
    {
        "id": "SM-10",
        "name": "Legacy Vision",
        "queries": [
            "legacy vision what your life represents last day earth beyond",
            "legacy byproduct living consistently driving why purpose",
            "legacy coaching session scoring vision long-term meaning",
            "driving why legacy closed loop system priority outcomes"
        ]
    },
    {
        "id": "SM-11",
        "name": "Integrity (Foundational)",
        "queries": [
            "integrity foundational not strategy who you are unblinded",
            "integrity mastery coaching scoring congruence actions values",
            "integrity meritocracy safety nets serving people truth",
            "integrity self mastery scoring what does integrous look like"
        ]
    },
    {
        "id": "SM-12",
        "name": "Fear Recognition & Action Despite It",
        "queries": [
            "fear recognition action despite it courage through fear not absence",
            "acting despite fear speaking into fear coaching session breakthrough",
            "fear recognition mastery scoring navigating through fear",
            "fear as signal not stop sign coaching action despite fear"
        ]
    }
]

def get_embedding(text):
    """Get embedding via OpenRouter."""
    resp = requests.post(
        'https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()['data'][0]['embedding']

def query_index(pc, index_name, query_text, namespace=None, top_k=5):
    """Query a Pinecone index."""
    embedding = get_embedding(query_text)
    idx = pc.Index(index_name)
    kwargs = {
        'vector': embedding,
        'top_k': top_k,
        'include_metadata': True
    }
    if namespace:
        kwargs['namespace'] = namespace
    results = idx.query(**kwargs)
    return results.get('matches', [])

def extract_text(match):
    """Extract text from a Pinecone match."""
    meta = match.get('metadata', {})
    text = meta.get('text', meta.get('content', meta.get('chunk_text', '')))
    return text[:1500]  # Cap at 1500 chars

def mine_dimension(dimension, pc_primary, pc_strata):
    """Mine all vectors for a single Self Mastery dimension."""
    print(f"\n{'='*60}")
    print(f"Mining: {dimension['id']} — {dimension['name']}")
    print(f"{'='*60}")
    
    all_vectors = []
    
    for query in dimension['queries']:
        # Query ublib2 (primary)
        try:
            matches = query_index(pc_primary, 'ublib2', query, top_k=3)
            for m in matches:
                if m['score'] > 0.45:
                    text = extract_text(m)
                    if text and len(text) > 50:
                        all_vectors.append({
                            'source': 'ublib2',
                            'score': round(m['score'], 4),
                            'text': text
                        })
            print(f"  ublib2 [{query[:50]}...]: {len(matches)} matches")
        except Exception as e:
            print(f"  ublib2 ERROR: {e}")
        
        # Query ultimatestratabrain (all 4 namespaces)
        for ns in ['eeistratabrain', 'domstratabrain', 'igestratabrain', 'rtistratabrain']:
            try:
                matches = query_index(pc_strata, 'ultimatestratabrain', query, namespace=ns, top_k=2)
                for m in matches:
                    if m['score'] > 0.45:
                        text = extract_text(m)
                        if text and len(text) > 50:
                            all_vectors.append({
                                'source': f'strata/{ns}',
                                'score': round(m['score'], 4),
                                'text': text
                            })
                if matches:
                    print(f"  strata/{ns} [{query[:40]}...]: {len(matches)} matches")
            except Exception as e:
                print(f"  strata/{ns} ERROR: {e}")
        
        time.sleep(0.3)  # Rate limiting
    
    # Deduplicate by text similarity (exact match)
    seen = set()
    unique_vectors = []
    for v in all_vectors:
        key = v['text'][:200]
        if key not in seen:
            seen.add(key)
            unique_vectors.append(v)
    
    # Sort by score
    unique_vectors.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n  → {len(unique_vectors)} unique high-relevance vectors found")
    return unique_vectors[:15]  # Top 15 per dimension

def synthesize_with_llm(dimension, vectors):
    """Use LLM to extract creature-level anchors from mined vectors."""
    if not vectors:
        return f"No high-relevance vectors found for {dimension['name']}."
    
    vector_text = "\n\n---\n\n".join([
        f"[Source: {v['source']}, Score: {v['score']}]\n{v['text']}" 
        for v in vectors[:12]
    ])
    
    prompt = f"""You are analyzing Sean Callagy's actual teachings from ublib2 and ultimatestratabrain 
to extract CONCRETE creature-level calibration anchors for the Formula Judge.

**Dimension:** {dimension['id']} — {dimension['name']}

**Your task:** From the vectors below, extract what Sean ACTUALLY said or demonstrated about 
different mastery levels for this dimension. Map to the creature scale:

- **Gecko (3.0-4.0):** What does POOR look like? What are the symptoms?
- **Komodo (5.0-6.0):** What does DEVELOPING look like? Some awareness, inconsistent.
- **Eagle (7.0-8.0):** What does PROFICIENT look like? Consistent execution with gaps.
- **Lion (8.5-9.0):** What does EXCELLENT look like? Near-mastery, few gaps.
- **Godzilla (9.5+):** What does TRANSCENDENT look like? Sean-level. Integration, not effort.

**Rules:**
1. Use Sean's ACTUAL words where possible (quote directly)
2. Give CONCRETE behaviors/indicators, not abstract descriptions
3. If you can't find evidence for a creature level, say "No anchor found — needs more data"
4. Show the COST of being at a lower level (what it destroys downstream)
5. Show the CAUSE at higher levels (what it enables upstream)

**Vectors from Sean's knowledge base:**

{vector_text}

Output format:
### {dimension['name']} — Creature Level Anchors

**Gecko (3.0-4.0):** [concrete description with quotes]
**Komodo (5.0-6.0):** [concrete description with quotes]
**Eagle (7.0-8.0):** [concrete description with quotes]
**Lion (8.5-9.0):** [concrete description with quotes]  
**Godzilla (9.5+):** [concrete description with quotes]

**Key Sean Quotes:**
- [direct quotes that anchor the scoring]

**What This Dimension Costs When Missing:**
[downstream destruction]

**What This Dimension Enables When Present:**
[upstream creation]
"""
    
    resp = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'anthropic/claude-opus-4.6',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 2000,
            'temperature': 0.3
        },
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']

def main():
    print("=" * 70)
    print("SELF MASTERY CALIBRATION MINER — Phase 1")
    print("Mining ublib2 + ultimatestratabrain for creature-level anchors")
    print("=" * 70)
    
    # Initialize Pinecone clients
    pc_primary = Pinecone(api_key=PINECONE_API_KEY)
    pc_strata = Pinecone(api_key=PINECONE_API_KEY_STRATA)
    
    # Mine all dimensions
    all_results = {}
    for dim in SELF_MASTERY_DIMENSIONS:
        vectors = mine_dimension(dim, pc_primary, pc_strata)
        all_results[dim['id']] = {
            'dimension': dim,
            'vectors': vectors
        }
    
    # Synthesize with LLM
    print("\n\n" + "=" * 70)
    print("PHASE 2: LLM SYNTHESIS — Extracting Creature-Level Anchors")
    print("=" * 70)
    
    report_sections = []
    report_sections.append("# Self Mastery Calibration Anchors — Formula Judge Grounding")
    report_sections.append(f"\n_Mined from ublib2 (58K vectors) + ultimatestratabrain (39K vectors)_")
    report_sections.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M EST')}_")
    report_sections.append(f"\n---\n")
    report_sections.append("## Purpose\n")
    report_sections.append("Turn the Formula Judge from 'our best guess at Sean's standard' into")
    report_sections.append("'Sean's standard, proven from his own words.' Each dimension below")
    report_sections.append("has creature-level anchors extracted from Sean's actual teachings —")
    report_sections.append("real coaching sessions, real moments, real interventions.\n")
    report_sections.append("## The 13 Self Mastery Dimensions\n")
    
    total_vectors = 0
    for dim_id, data in all_results.items():
        dim = data['dimension']
        vectors = data['vectors']
        total_vectors += len(vectors)
        
        print(f"\nSynthesizing {dim['id']} — {dim['name']} ({len(vectors)} vectors)...")
        
        synthesis = synthesize_with_llm(dim, vectors)
        report_sections.append(f"\n---\n\n## {dim['id']}: {dim['name']}\n")
        report_sections.append(f"_Vectors mined: {len(vectors)} | Sources: ublib2 + ultimatestratabrain_\n")
        report_sections.append(synthesis)
        
        time.sleep(1)  # Rate limiting between LLM calls
    
    # Summary stats
    report_sections.append(f"\n\n---\n\n## Mining Statistics\n")
    report_sections.append(f"- **Total unique vectors mined:** {total_vectors}")
    report_sections.append(f"- **Dimensions analyzed:** {len(SELF_MASTERY_DIMENSIONS)}")
    report_sections.append(f"- **Sources:** ublib2 (primary, 58K vectors) + ultimatestratabrain (4 namespaces, 39K vectors)")
    report_sections.append(f"- **Minimum relevance threshold:** 0.45 cosine similarity")
    report_sections.append(f"\n## Next Steps\n")
    report_sections.append(f"1. **Validate with Kai** — Send through sister webhook for Translator calibration")
    report_sections.append(f"2. **Mine Influence Mastery** — 12 components, same methodology")
    report_sections.append(f"3. **Mine Process Mastery** — 15 components, same methodology")
    report_sections.append(f"4. **Feed into Formula Judge** — These anchors become the scoring rubric")
    report_sections.append(f"5. **Sean + Adam review** — Final calibration against lived expertise")
    
    # Write report
    os.makedirs('reports', exist_ok=True)
    report_path = 'reports/self-mastery-calibration-anchors.md'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_sections))
    
    print(f"\n{'='*70}")
    print(f"REPORT WRITTEN: {report_path}")
    print(f"Total vectors: {total_vectors} across {len(SELF_MASTERY_DIMENSIONS)} dimensions")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
