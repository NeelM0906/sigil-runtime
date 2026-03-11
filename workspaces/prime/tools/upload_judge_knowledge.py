#!/usr/bin/env python3
"""
Upload judge knowledge to acti-judges Pinecone index.
Sorts mined content from strata-mine files into 47 skill cluster namespaces.
"""

import os
import sys
import re
import json
import hashlib
import time
import requests
from pinecone import Pinecone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
VENV_DIR = os.path.dirname(os.path.dirname(VENV_PYTHON))
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.prefix) != os.path.realpath(VENV_DIR):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

# Namespace mapping — 47 skill clusters
NAMESPACE_MAP = {
    # D1: Written Communication
    'd1-short-form': ['headline', 'subject line', 'CTA', 'call to action', 'hook', 'ad copy', 'short-form', 'tagline'],
    'd1-long-form': ['blog', 'book', 'thought leadership', 'case study', 'article', 'long-form', 'narrative', 'whitepaper'],
    'd1-conversion': ['landing page', 'sales page', 'deposit page', 'conversion copy', 'squeeze page', 'opt-in'],
    'd1-sequence': ['email sequence', 'drip', 'nurture', 'VANS', 'onboarding email', 'follow-up', 'automation sequence'],
    'd1-brand-voice': ['brand copy', 'brand voice', 'press release', 'company narrative', 'mission statement', 'social copy'],
    'd1-editorial': ['editing', 'proofing', 'style guide', 'QA', 'grammar', 'revision', 'editorial'],
    
    # D2: Visual & Creative
    'd2-graphic-design': ['graphic design', 'ad creative', 'social graphic', 'brand asset', 'visual design', 'layout'],
    'd2-video': ['video', 'editing', 'cinematography', 'B-roll', 'thumbnail', 'frame rate', 'resolution', 'color grading', 'hook rate', 'smoothness'],
    'd2-audio': ['audio', 'podcast', 'recording', 'mixing', 'mastering', 'sound engineer', 'noise floor', 'sample rate'],
    'd2-ux-ui': ['UX', 'UI', 'wireframe', 'user flow', 'interface', 'usability', 'conversion interface'],
    'd2-brand-identity': ['brand identity', 'style guide', 'visual system', 'logo', 'color palette', 'typography'],
    'd2-presentation': ['deck', 'presentation', 'stage visual', 'webinar asset', 'slide'],
    
    # D3: Data & Analytics
    'd3-business-intel': ['dashboard', 'KPI', 'business intelligence', 'reporting', 'BI', 'data visualization'],
    'd3-data-sourcing': ['data sourcing', 'list building', 'enrichment', 'scraping', 'validation', 'dedup', 'contact data'],
    'd3-conversion-opt': ['A/B test', 'CRO', 'conversion optimization', 'split test', 'funnel analytics', 'statistical significance'],
    'd3-seo': ['SEO', 'keyword', 'ranking', 'organic search', 'technical audit', 'backlink', 'SERP'],
    'd3-ml-ai': ['machine learning', 'ML', 'AI model', 'training data', 'deployment', 'prompt engineering', 'neural'],
    'd3-financial-analytics': ['revenue model', 'forecasting', 'variance analysis', 'financial analytics', 'projection'],
    'd3-market-research': ['competitive analysis', 'market research', 'audience segmentation', 'trend', 'TAM', 'SAM'],
    
    # D4: Strategic Planning
    'd4-campaign': ['campaign', 'lever sequence', 'multi-channel', 'campaign architecture', 'timeline', 'phasing'],
    'd4-media-buying': ['media buy', 'budget allocation', 'CPA', 'ROAS', 'ad spend', 'saturation', 'channel optimization', 'CPL'],
    'd4-ecosystem': ['ecosystem', 'partnership', 'value exchange', 'merger', 'collaboration', 'strategic alliance'],
    'd4-gtm': ['go-to-market', 'launch', 'positioning', 'market entry', 'GTM'],
    'd4-competitive': ['competitive strategy', 'differentiation', 'positioning', 'response playbook', 'competitor'],
    
    # D5: Human Influence
    'd5-sales': ['agreement formation', 'objection', 'closing', 'deposit', 'sales conversation', 'negotiation'],
    'd5-coaching': ['coaching', 'BAS', 'actualizing session', 'cert call', 'diagnostic', 'breakthrough'],
    'd5-community': ['community', 'group dynamics', 'engagement', 'culture building', 'facilitation'],
    'd5-intake': ['intake', 'qualification', 'lead qual', 'needs assessment', 'routing', 'discovery call'],
    'd5-stage': ['keynote', 'webinar', 'public speaking', 'stage', 'presentation delivery', 'audience engagement'],
    
    # D6: Operations & Fulfillment
    'd6-project': ['project management', 'timeline', 'resource allocation', 'stakeholder', 'milestone', 'PMI'],
    'd6-onboarding': ['onboarding', 'first 90 days', 'welcome', 'member onboarding', 'client onboarding'],
    'd6-delivery': ['fulfillment', 'SLA', 'delivery', 'escalation', 'service level', 'turnaround'],
    'd6-qa': ['quality assurance', 'QA', 'error detection', 'standards enforcement', 'defect rate', 'review'],
    'd6-process-opt': ['process optimization', 'workflow', 'automation', 'bottleneck', 'efficiency', 'lean'],
    'd6-events': ['event operations', 'logistics', 'vendor', 'day-of', 'event management', 'AV'],
    
    # D7: Financial & Legal
    'd7-revops': ['revenue operations', 'RevOps', 'pricing', 'billing', 'collection', 'NRR', 'churn'],
    'd7-tax': ['tax strategy', 'entity structure', 'tax compliance', 'Cayman', 'S-Corp', 'LLC', 'restructuring'],
    'd7-recovery': ['medical recovery', 'insurance', 'claims', 'underpayment', 'fee schedule', 'appeal', 'denial'],
    'd7-legal': ['legal compliance', 'contract', 'risk assessment', 'regulatory', 'audit', 'HIPAA', 'GDPR'],
    'd7-financial-planning': ['budget', 'forecasting', 'cash flow', 'financial planning', 'P&L', 'balance sheet', 'ROIC'],
    'd7-disposable': ['margin', 'cost optimization', 'profit', 'disposable income', 'expense reduction'],
    
    # D8: Technology & Engineering
    'd8-platform': ['full-stack', 'frontend', 'backend', 'database', 'web development', 'API development'],
    'd8-ai-ml': ['AI implementation', 'model training', 'prompt engineering', 'LLM', 'fine-tuning', 'inference'],
    'd8-integration': ['API', 'integration', 'data pipeline', 'webhook', 'sync', 'middleware', 'connectivity'],
    'd8-automation': ['workflow automation', 'trigger', 'n8n', 'Zapier', 'Make', 'cron', 'scheduled'],
    'd8-tools': ['CRM', 'marketing automation', 'Salesforce', 'HubSpot', 'analytics platform', 'configuration'],
    'd8-security': ['security', 'vulnerability', 'uptime', 'MTTR', 'data protection', 'access control', 'encryption'],
}

def get_embedding(text):
    """Get embedding via OpenRouter."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    resp = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {api_key}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]})
    return resp.json()['data'][0]['embedding']

def classify_chunk(text):
    """Classify a text chunk into the best matching namespace."""
    text_lower = text.lower()
    scores = {}
    for ns, keywords in NAMESPACE_MAP.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[ns] = score
    if not scores:
        return None
    return max(scores, key=scores.get)

def chunk_file(filepath, chunk_size=500):
    """Split a markdown file into chunks by sections."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by headers or double newlines
    sections = re.split(r'\n(?=#{1,3} |\n\n---)', content)
    
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > chunk_size and current:
            chunks.append(current.strip())
            current = section
        else:
            current += "\n" + section
    if current.strip():
        chunks.append(current.strip())
    
    return [c for c in chunks if len(c) > 50]  # Skip tiny chunks

def upload_file(filepath, index, dry_run=False):
    """Process and upload a mined file to Pinecone."""
    print(f"\n📂 Processing: {filepath}")
    chunks = chunk_file(filepath)
    print(f"   Found {len(chunks)} chunks")
    
    ns_counts = {}
    uploaded = 0
    skipped = 0
    
    for i, chunk in enumerate(chunks):
        ns = classify_chunk(chunk)
        if not ns:
            skipped += 1
            continue
        
        ns_counts[ns] = ns_counts.get(ns, 0) + 1
        
        if not dry_run:
            try:
                embedding = get_embedding(chunk)
                vec_id = hashlib.md5(chunk[:200].encode()).hexdigest()
                
                index.upsert(
                    vectors=[{
                        'id': f"judge-{ns}-{vec_id}",
                        'values': embedding,
                        'metadata': {
                            'text': chunk[:2000],
                            'namespace_cluster': ns,
                            'source_file': os.path.basename(filepath),
                            'domain': ns.split('-')[0],
                            'type': 'judge_knowledge'
                        }
                    }],
                    namespace=ns
                )
                uploaded += 1
                if uploaded % 10 == 0:
                    print(f"   Uploaded {uploaded}...")
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"   ❌ Error on chunk {i}: {e}")
                skipped += 1
        else:
            uploaded += 1
    
    print(f"   ✅ Uploaded: {uploaded} | Skipped: {skipped}")
    print(f"   Namespace distribution: {json.dumps(ns_counts, indent=2)}")
    return uploaded, skipped, ns_counts

def main():
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN — classifying only, no uploads")
    else:
        print("🚀 UPLOADING to acti-judges index")
    
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    index = pc.Index('acti-judges')
    
    reports_dir = os.path.join(SCRIPT_DIR, '..', 'reports')
    mine_files = [
        os.path.join(reports_dir, 'strata-mine-d1-d2.md'),
        os.path.join(reports_dir, 'strata-mine-d3-d4.md'),
        os.path.join(reports_dir, 'strata-mine-d5-d6.md'),
        os.path.join(reports_dir, 'strata-mine-d7-d8.md'),
    ]
    
    total_uploaded = 0
    total_skipped = 0
    all_ns = {}
    
    for f in mine_files:
        if os.path.exists(f):
            u, s, ns = upload_file(f, index, dry_run)
            total_uploaded += u
            total_skipped += s
            for k, v in ns.items():
                all_ns[k] = all_ns.get(k, 0) + v
        else:
            print(f"⚠️ Missing: {f}")
    
    print(f"\n{'='*50}")
    print(f"TOTAL: {total_uploaded} uploaded | {total_skipped} skipped")
    print(f"Namespaces populated: {len(all_ns)}")
    print(f"\nNamespace breakdown:")
    for ns, count in sorted(all_ns.items()):
        print(f"  {ns}: {count} vectors")

if __name__ == '__main__':
    main()
