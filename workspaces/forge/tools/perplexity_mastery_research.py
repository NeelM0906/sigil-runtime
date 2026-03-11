#!/usr/bin/env python3
"""
Perplexity-Powered Mastery Research → acti-judges

Uses web_search (Perplexity/Brave) to get real-world technical grounding,
then embeds into acti-judges with source=web tag.

Usage: python3 tools/perplexity_mastery_research.py "namespace" "Domain Name"
Or batch: python3 tools/perplexity_mastery_research.py --batch
"""
import os, sys, json, hashlib, requests, time
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
BRAVE_KEY = os.environ.get('BRAVE_API_KEY', '') or os.environ.get('SEARCH_API_KEY', '')

# Technical domains that benefit most from live web research
TECHNICAL_NAMESPACES = [
    ("api-development-and-system-integration", "API Development & System Integration"),
    ("data-engineering-and-etl-pipelines", "Data Engineering & ETL Pipelines"),
    ("cybersecurity-and-information-security", "Cybersecurity & Information Security"),
    ("prompt-engineering-and-ai-architecture", "Prompt Engineering & AI Architecture"),
    ("web-development-and-engineering", "Web Development & Engineering"),
    ("data-analytics-and-business-intelligence", "Data Analytics & Business Intelligence"),
    ("automation-and-workflow-orchestration", "Automation & Workflow Orchestration"),
    ("product-management-and-strategy", "Product Management & Strategy"),
    ("software-engineering-and-architecture", "Software Engineering & Architecture"),
    ("machine-learning-and-ai-development", "Machine Learning & AI Development"),
]

def web_search(query, num_results=5):
    """Search for real-world technical content via Brave or Perplexity."""
    if BRAVE_KEY:
        r = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers={'Accept': 'application/json', 'X-Subscription-Token': BRAVE_KEY},
            params={'q': query, 'count': num_results},
            timeout=30
        )
        if r.status_code == 200:
            results = r.json().get('web', {}).get('results', [])
            return '\n\n'.join([f"**{r.get('title')}**\n{r.get('description','')}\nURL: {r.get('url','')}" 
                              for r in results[:num_results]])
    
    # Fallback: use OpenRouter with online model (Perplexity-style)
    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={
            'model': 'perplexity/sonar-pro',
            'messages': [{'role': 'user', 'content': query}],
            'max_tokens': 2000
        }, timeout=60)
    if r.status_code == 200:
        return r.json()['choices'][0]['message']['content']
    return None

def research_domain_web(namespace, domain_name):
    """Use web search to get real-world technical mastery data."""
    queries = [
        f"{domain_name} mastery 2024 2025 top certifications best practices industry standards",
        f"{domain_name} expert skills tools platforms real-world benchmarks performance metrics",
        f"{domain_name} common failures red flags what separates junior from senior expert",
        f"{domain_name} Formula integration influence persuasion agreement formation sales",
    ]
    
    all_research = []
    for q in queries[:3]:  # 3 searches per domain
        result = web_search(q)
        if result:
            all_research.append(f"QUERY: {q}\n\n{result}")
        time.sleep(1)
    
    if not all_research:
        return None
    
    combined = '\n\n---\n\n'.join(all_research)
    
    # Synthesize with LLM
    synthesis_prompt = f"""You are building judge intelligence for the ACT-I Colosseum — an AI tournament that evaluates beings on professional mastery.

Domain: {domain_name}

Web research gathered:
{combined[:8000]}

Create a dense technical intelligence report (800-1000 words) covering:
1. **Real certifications & credentials** that signal mastery (specific names, bodies, levels)
2. **Actual tools & platforms** masters use (with specifics, not generic lists)
3. **Current industry benchmarks** — what separates 99th percentile from 90th percentile
4. **Real failure patterns** — specific mistakes practitioners make with concrete consequences
5. **Formula integration** — how trust, influence, and agreement formation apply in this domain specifically

Ground everything in real-world specifics from the research. A judge using this should be able to distinguish a true expert from someone who read the Wikipedia page.

Write dense, specific, and diagnostic. No fluff."""

    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={
            'model': 'anthropic/claude-opus-4-5',
            'messages': [{'role': 'user', 'content': synthesis_prompt}],
            'max_tokens': 2000
        }, timeout=120)
    
    return r.json()['choices'][0]['message']['content']

def embed_text(text):
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    return r.json()['data'][0]['embedding']

def upload_to_judges(namespace, domain_name, content):
    """Upload web-researched content as additional vector in acti-judges."""
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')
    
    vid = f"{namespace}-web-research-{hashlib.md5(f'{namespace}-perplexity'.encode()).hexdigest()[:10]}"
    embedding = embed_text(content)
    
    idx.upsert(vectors=[{
        'id': vid,
        'values': embedding,
        'metadata': {
            'text': content,
            'namespace': namespace,
            'domain': domain_name,
            'section': 'web_research',
            'section_title': 'WEB-GROUNDED TECHNICAL INTELLIGENCE',
            'type': 'judge_enrichment',
            'source': 'perplexity_web_research',
            'version': 'v1'
        }
    }], namespace=namespace)

def main(namespace=None, domain_name=None, batch=False):
    targets = []
    
    if batch or '--batch' in sys.argv:
        targets = TECHNICAL_NAMESPACES
    elif namespace:
        targets = [(namespace, domain_name or namespace.replace('-', ' ').title())]
    else:
        targets = TECHNICAL_NAMESPACES[:3]  # Default: top 3
    
    print(f"⚔️ Perplexity Mastery Research — {len(targets)} domains\n")
    
    for ns, domain in targets:
        print(f"[{domain}]")
        
        content = research_domain_web(ns, domain)
        if not content:
            print(f"  ❌ No content generated")
            continue
        
        print(f"  {len(content)} chars generated")
        
        upload_to_judges(ns, domain, content)
        print(f"  ✅ Uploaded to acti-judges/{ns} (source=web)")
        print()
        
        time.sleep(3)
    
    print("⚔️ Done")

if __name__ == '__main__':
    if '--batch' in sys.argv:
        main(batch=True)
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith('--'):
        ns = sys.argv[1]
        domain = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        main(namespace=ns, domain_name=domain)
    else:
        main()
