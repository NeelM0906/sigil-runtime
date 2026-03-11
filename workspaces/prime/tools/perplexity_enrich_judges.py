#!/usr/bin/env python3
"""
Perplexity Web Research → acti-judges Pinecone enrichment.
Runs live web research per namespace, then embeds and uploads.
"""
import os, sys, json, hashlib, time, requests
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

def perplexity_research(namespace):
    """Run Perplexity web research for a namespace's technical mastery requirements."""
    human_name = namespace.replace('-', ' ').title()
    
    queries = [
        f"What are the top certifications, tools, and platforms that professionals in {human_name} must master in 2025-2026? Include specific software names, certification bodies, and industry standards.",
        f"What are the current best practices and emerging trends in {human_name}? Include real benchmarks, KPIs, and performance standards used by top practitioners.",
        f"What are the most common failure patterns and career-limiting mistakes in {human_name}? Include specific examples from industry case studies."
    ]
    
    all_results = []
    for q in queries:
        try:
            r = requests.post('https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'perplexity/sonar-pro',
                    'messages': [{'role': 'user', 'content': q}],
                    'max_tokens': 4000,
                }, timeout=60)
            
            resp = r.json()
            if 'error' in resp:
                print(f"  Perplexity error: {resp['error']}")
                continue
            content = resp['choices'][0]['message']['content']
            all_results.append(f"QUERY: {q}\n\nRESEARCH:\n{content}")
            time.sleep(1)  # Rate limit between queries
        except Exception as e:
            print(f"  Research error: {e}")
            continue
    
    return '\n\n---\n\n'.join(all_results)


def embed_text(text):
    """Get embedding via OpenRouter."""
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    data = r.json()
    if 'error' in data:
        print(f"  Embed error: {data['error']}")
        return None
    return data['data'][0]['embedding']


def upload_research(namespace, research_text):
    """Upload Perplexity research as vectors to acti-judges."""
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('acti-judges')
    
    now = datetime.now(timezone.utc).isoformat()
    human_name = namespace.replace('-', ' ').title()
    
    # Split research into chunks (~2000 chars each)
    chunks = []
    current = ""
    for line in research_text.split('\n'):
        if len(current) + len(line) > 2000 and current:
            chunks.append(current.strip())
            current = line + '\n'
        else:
            current += line + '\n'
    if current.strip():
        chunks.append(current.strip())
    
    uploaded = 0
    for i, chunk in enumerate(chunks):
        if len(chunk) < 100:
            continue
            
        embedding = embed_text(chunk)
        if not embedding:
            continue
        
        vid = f"perplexity-{hashlib.md5(f'{namespace}-{i}'.encode()).hexdigest()[:12]}"
        
        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': chunk[:40000],
                'cluster': human_name,
                'section': f'PERPLEXITY_RESEARCH_CHUNK_{i+1}',
                'type': 'web_research',
                'source': 'perplexity/sonar-pro',
                'uploaded_at': now,
            }
        }], namespace=namespace)
        
        uploaded += 1
        time.sleep(0.2)
    
    return uploaded


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespaces', nargs='+', help='Specific namespaces to research')
    parser.add_argument('--all', action='store_true', help='Research all namespaces')
    parser.add_argument('--batch-file', help='File with namespace list')
    args = parser.parse_args()
    
    if args.batch_file:
        with open(args.batch_file) as f:
            namespaces = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    elif args.namespaces:
        namespaces = args.namespaces
    elif args.all:
        pc = Pinecone(api_key=PINECONE_KEY)
        idx = pc.Index('acti-judges')
        stats = idx.describe_index_stats()
        # Only research skill-named namespaces (not d1-, d2- etc)
        namespaces = sorted([k for k in stats.namespaces.keys() if '-' in k and not k.startswith('d') or k.startswith('d') and len(k) > 10])
    else:
        parser.print_help()
        return
    
    total_vectors = 0
    for i, ns in enumerate(namespaces):
        print(f"\n[{i+1}/{len(namespaces)}] Researching: {ns}")
        
        research = perplexity_research(ns)
        if not research:
            print(f"  SKIP: No research returned")
            continue
        
        print(f"  Research: {len(research)} chars")
        
        # Save raw research
        out_dir = Path.home() / '.openclaw' / 'workspace' / 'reports' / 'perplexity-research'
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{ns}.md").write_text(research)
        
        vectors = upload_research(ns, research)
        total_vectors += vectors
        print(f"  Uploaded: {vectors} vectors → acti-judges/{ns}")
        
        time.sleep(2)  # Rate limit between namespaces
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {total_vectors} web research vectors across {len(namespaces)} namespaces")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
