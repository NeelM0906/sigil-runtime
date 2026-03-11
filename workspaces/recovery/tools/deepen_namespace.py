#!/usr/bin/env python3
"""
Deepen a namespace in acti-judges from 1 vector → 6-7 vectors.
Each section of mastery research becomes its own vector for precise retrieval.

Usage: python3 deepen_namespace.py "cluster name" "namespace-slug"
"""
import os, sys, json, hashlib, requests
from pathlib import Path
from datetime import datetime

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

SECTIONS = [
    ("domain_overview", "Domain definition, scope, and why mastery here matters"),
    ("core_competencies", "Core competencies and skills required for mastery (9.0+ level)"),
    ("mastery_indicators", "What a master looks like in action — specific behaviors, outputs, and signals that distinguish expert from amateur"),
    ("failure_patterns", "Top failure patterns — what 6.0-7.0 practitioners do wrong, where they plateau, common mistakes"),
    ("formula_integration", "How the Unblinded Formula applies: self-mastery, influence mastery, process mastery, and GHIC principles in this domain"),
    ("tools_and_resources", "Best tools, platforms, textbooks, certifications, and resources for mastering this domain"),
    ("colosseum_scenarios", "3 specific Colosseum test scenarios that distinguish a master from an amateur in this exact domain — concrete prompts with expected master response patterns"),
]

def research_section(cluster_name: str, section_key: str, section_prompt: str) -> str:
    prompt = f"""You are a domain mastery expert for the Colosseum judging system.

Cluster: "{cluster_name}"
Section: {section_key}
Task: {section_prompt}

Write a dense, specific, expert-level analysis of THIS section for "{cluster_name}".
- Be concrete and specific, not generic
- Use real-world examples from this domain
- Think at the 9.0+ mastery level
- For Formula Integration: connect directly to Sean Callagy's Unblinded Formula principles
- For Colosseum Scenarios: write prompts that actually test mastery, not knowledge recall

Write 400-600 words. No headers. Just dense expert content."""

    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={
            'model': 'anthropic/claude-opus-4.6',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1000
        }, timeout=90)
    return r.json()['choices'][0]['message']['content']

def embed_text(text: str) -> list:
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text},
        timeout=30)
    return r.json()['data'][0]['embedding']

def deepen(cluster_name: str, namespace: str):
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')

    # Check current state
    stats = idx.describe_index_stats()
    current = stats.namespaces.get(namespace, None)
    current_count = current.vector_count if current else 0
    print(f"Current vectors in {namespace}: {current_count}")
    print(f"Adding {len(SECTIONS)} section vectors...\n")

    uploaded = 0
    for section_key, section_prompt in SECTIONS:
        print(f"  Researching section: {section_key}...")
        content = research_section(cluster_name, section_key, section_prompt)
        embedding = embed_text(content)

        vid = f"{namespace}-{section_key}-{hashlib.md5(content[:100].encode()).hexdigest()[:6]}"
        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': content,
                'cluster': cluster_name,
                'section': section_key,
                'type': 'section_depth',
                'source': 'deepen_namespace',
                'uploaded_at': datetime.utcnow().isoformat()
            }
        }], namespace=namespace)
        uploaded += 1
        print(f"  ✅ {section_key} ({len(content)} chars)")

    print(f"\n✅ Done. {uploaded} new vectors added to acti-judges/{namespace}")
    print(f"   Total now: ~{current_count + uploaded}")

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        cluster = sys.argv[1]
        ns = sys.argv[2]
        deepen(cluster, ns)
    elif len(sys.argv) == 2:
        cluster = sys.argv[1]
        ns = cluster.lower().replace(' ', '-').replace('&', 'and')
        deepen(cluster, ns)
    else:
        print("Usage: python3 deepen_namespace.py 'Cluster Name' 'namespace-slug'")
