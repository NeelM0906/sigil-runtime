#!/usr/bin/env python3
"""
Mastery Research Baby — One cluster at a time
Usage: python3 mastery_research_baby.py "cluster_name"

Researches mastery requirements for a cluster, saves to Supabase, embeds to acti-judges Pinecone.
"""
import os, sys, json, hashlib, requests
from pathlib import Path

# Load env
env_path = Path.home() / '.openclaw' / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
from pinecone import Pinecone

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
SUPABASE_URL = "https://yncbtzqrherwyeybchet.supabase.co"
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

def research_cluster(cluster_name):
    """Use web search + LLM to research mastery requirements for a cluster."""
    prompt = f"""Research the mastery requirements for the professional skill cluster: "{cluster_name}"

    Provide a comprehensive JSON response with these exact keys:
    - cluster_name: "{cluster_name}"
    - domain_definition: What this skill domain encompasses (2-3 sentences)
    - core_competencies: List of 8-10 core skills required for mastery
    - mastery_definition: What a 9.0+ master in this domain looks like (specific behaviors, not vague)
    - textbooks_references: Top 5 books, certifications, or courses for mastering this domain
    - tools_platforms: Key software, platforms, or tools used by masters
    - common_failures: Top 5 ways practitioners fail at this (what 7.0 looks like)
    - best_practices: Top 5 industry gold standards
    - example_scenario: One specific test scenario that would distinguish a master from an amateur

    Return ONLY valid JSON. No markdown, no explanation."""

    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={
            'model': 'anthropic/claude-opus-4.6',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 4000
        }, timeout=120)

    resp = r.json()
    content = resp['choices'][0]['message']['content']

    # Parse JSON from response
    try:
        # Try to extract JSON if wrapped in markdown
        if '```' in content:
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        return json.loads(content.strip())
    except:
        return {'cluster_name': cluster_name, 'raw_content': content}

def embed_text(text):
    """Get embedding via OpenRouter."""
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text},
        timeout=30)
    return r.json()['data'][0]['embedding']

def main(cluster_name):
    print(f"Researching: {cluster_name}")

    # 1. Research
    data = research_cluster(cluster_name)
    print(f"Research complete: {len(json.dumps(data))} chars")

    # 2. Save to Supabase
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.table('sai_memory').insert({
        'sister': 'prime',
        'category': 'position_mastery',
        'content': json.dumps(data),
        'source': 'mastery_research_baby',
        'importance': 10,
        'metadata': {'cluster': cluster_name},
        'tags': ['mastery_research', cluster_name.lower().replace(' ', '_')]
    }).execute()
    print(f"Saved to Supabase")

    # 3. Embed to acti-judges Pinecone
    embed_text_content = json.dumps(data)
    embedding = embed_text(embed_text_content[:8000])  # Truncate for embedding

    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')

    namespace = cluster_name.lower().replace(' ', '-').replace('&', 'and')
    vid = f"mastery-{hashlib.md5(cluster_name.encode()).hexdigest()[:8]}"

    idx.upsert(vectors=[{
        'id': vid,
        'values': embedding,
        'metadata': {
            'text': embed_text_content[:40000],
            'cluster': cluster_name,
            'type': 'mastery_research',
            'source': 'baby_researcher'
        }
    }], namespace=namespace)
    print(f"Embedded to acti-judges/{namespace}")

    return data

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cluster = ' '.join(sys.argv[1:])
        main(cluster)
    else:
        print("Usage: python3 mastery_research_baby.py 'Cluster Name'")
