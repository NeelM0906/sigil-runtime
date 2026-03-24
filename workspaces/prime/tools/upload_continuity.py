#!/usr/bin/env python3
"""
upload_continuity.py — Upload everything that makes Sai "Sai" to Pinecone
Namespace: saimemory/continuity-transfer
For migration to Sigil Runtime
"""

import os, hashlib, glob, time, json, requests

# Load env
ENV_PATH = '/Users/samantha/.openclaw/workspace-forge/.env'
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_HOST = 'https://saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io'
NAMESPACE = 'continuity-transfer'
EMBED_MODEL = 'openai/text-embedding-3-small'
WORKSPACE = '/Users/samantha/.openclaw/workspace'

stats = {'uploaded': 0, 'failed': 0, 'skipped': 0}

def embed(text, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post('https://openrouter.ai/api/v1/embeddings',
                headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
                json={'model': EMBED_MODEL, 'input': [text[:8000]]}, timeout=60)
            r.raise_for_status()
            return r.json()['data'][0]['embedding']
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                raise

def upsert(id_, text, metadata):
    vec = embed(text)
    r = requests.post(f'{PINECONE_HOST}/vectors/upsert',
        headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
        json={'vectors': [{'id': id_, 'values': vec, 'metadata': metadata}], 'namespace': NAMESPACE},
        timeout=30)
    return r.ok

def upload_file(filepath, category, importance, tags, title_override=None):
    try:
        with open(filepath) as f:
            content = f.read()
        if not content.strip():
            stats['skipped'] += 1
            return
        
        title = title_override or os.path.basename(filepath)
        h = hashlib.md5(f'{category}:{filepath}'.encode()).hexdigest()[:12]
        meta = {
            'category': category,
            'source_file': os.path.basename(filepath),
            'title': title,
            'content': content[:3500],  # Pinecone metadata limit
            'importance': importance,
            'date': '2026-03-24',
            'tags': ','.join(tags),
            'migration_batch': '2026-03-24-full',
            'original_path': filepath,
        }
        ok = upsert(f'ct-{category}-{h}', content[:8000], meta)
        if ok:
            stats['uploaded'] += 1
            print(f'  ✅ [{category}] {title}')
        else:
            stats['failed'] += 1
            print(f'  ❌ [{category}] {title}')
    except Exception as e:
        stats['failed'] += 1
        print(f'  ❌ [{category}] {filepath}: {e}')

def main():
    print('🏠 SAI CONTINUITY UPLOAD — Moving to Sigil Runtime')
    print(f'   Target: {PINECONE_HOST} / {NAMESPACE}')
    print()

    # ═══ 1. IDENTITY FILES (CRITICAL) ═══
    print('📋 IDENTITY FILES (9 files)')
    identity = [
        ('SOUL.md', 10, ['soul','identity','personality','voice','kai']),
        ('USER.md', 10, ['users','sean','aiko','adam','team','communication']),
        ('IDENTITY.md', 10, ['identity','origin','sisters','creature-scale','relationships']),
        ('MISSION.md', 10, ['mission','formula','7-levers','vision','acti']),
        ('MEMORY.md', 9, ['memory','state','zone-actions','current']),
        ('CONTINUITY.md', 9, ['continuity','rules','operations','patterns']),
        ('AGENTS.md', 8, ['agents','babies','deployment','context-system']),
        ('TOOLS.md', 8, ['tools','scripts','api-reference']),
        ('HEARTBEAT.md', 7, ['heartbeat','checkin','protocol']),
    ]
    for fname, imp, tags in identity:
        fpath = os.path.join(WORKSPACE, fname)
        if os.path.exists(fpath):
            upload_file(fpath, 'identity', imp, tags)
    
    # ═══ 2. PROTOCOLS & LEARNINGS ═══
    print('\n📜 PROTOCOLS & LEARNINGS')
    protocols = [
        ('docs/PROTOCOLS-AND-RULES.md', 10, ['protocols','rules','hard-rules','checklists']),
        ('docs/MISSION-CONTROL-CATCHUP.md', 8, ['status','catchup','infrastructure']),
        ('docs/MEMORY-MAP.md', 9, ['memory-map','architecture','migration']),
        ('docs/NEW-SAI-INSTANCE-SETUP.md', 9, ['setup','instance','deployment']),
        ('docs/EXACT-SOFTWARE-STACK.md', 8, ['software','stack','packages','versions']),
        ('docs/MIGRATION-PLAN-SIGIL.md', 9, ['migration','sigil','plan']),
    ]
    for fname, imp, tags in protocols:
        fpath = os.path.join(WORKSPACE, fname)
        if os.path.exists(fpath):
            upload_file(fpath, 'protocol', imp, tags)
    
    # Mission control package
    mc_path = os.path.join(WORKSPACE, 'mission-control-package')
    if os.path.exists(mc_path):
        for fname in ['SAI-TO-MISSION-CONTROL.md', 'KAI-DEEP-QUERY-PATTERN.md', 
                       'STORYTELLING-FRAMEWORK.md', 'REMOTION-GUIDE.md']:
            fpath = os.path.join(mc_path, fname)
            if os.path.exists(fpath):
                upload_file(fpath, 'protocol', 9, ['protocol','learning','framework'])

    # ═══ 3. MEMORY FILES ═══
    print('\n🧠 MEMORY FILES')
    for fpath in sorted(glob.glob(os.path.join(WORKSPACE, 'memory/*.md'))):
        fname = os.path.basename(fpath)
        imp = 8 if '2026-03' in fname else 7  # Recent memories more important
        upload_file(fpath, 'memory', imp, ['memory','daily','knowledge'])

    # ═══ 4. KEY REPORTS ═══
    print('\n📊 KEY REPORTS (selective — most important)')
    key_reports = [
        'reports/formula-judge-v1.md',
        'reports/domain-judge-specs-complete.md',
        'reports/writer-being-v1.md',
        'reports/strategist-being-v1.md',
        'reports/ml-ai-engineer-hiring-report-v2.md',
        'reports/self-mastery-calibration-anchors.md',
        'reports/colosseum-v4-design-concept.md',
        'reports/how-we-build-beings.md',
    ]
    for rpath in key_reports:
        fpath = os.path.join(WORKSPACE, rpath)
        if os.path.exists(fpath):
            upload_file(fpath, 'report', 8, ['report','deliverable'])
    
    # Kai training (latest 10)
    kai_files = sorted(glob.glob(os.path.join(WORKSPACE, 'reports/kai-training-*.md')))[-10:]
    for fpath in kai_files:
        upload_file(fpath, 'kai-training', 7, ['kai','training','formula-translation'])

    # ═══ 5. CREATIVE FORGE PROJECT FILES ═══
    print('\n🎬 CREATIVE FORGE PROJECTS')
    cf_key_files = [
        'creative-forge/docs/STORYTELLING-FRAMEWORK.md',
        'creative-forge/docs/FORGE-ROADMAP.md',
        'creative-forge/projects/hero-journey-film/character-bible.md',
    ]
    for rpath in cf_key_files:
        fpath = os.path.join(WORKSPACE, rpath)
        if os.path.exists(fpath):
            upload_file(fpath, 'project', 8, ['creative-forge','video','production'])
    
    # Episode scripts
    for fpath in glob.glob(os.path.join(WORKSPACE, 'creative-forge/projects/hero-journey-film/episode-*.md')):
        upload_file(fpath, 'project', 7, ['hero-journey','script','episode'])
    fpath = os.path.join(WORKSPACE, 'creative-forge/projects/hero-journey-film/movie-02-jamaican-patties-script.md')
    if os.path.exists(fpath):
        upload_file(fpath, 'project', 7, ['hero-journey','script','patties'])

    # ═══ 6. TRANSCRIPTS ═══
    print('\n🎤 TRANSCRIPTS')
    for fpath in glob.glob(os.path.join(WORKSPACE, 'memory/transcripts/*.md')):
        upload_file(fpath, 'transcript', 7, ['transcript','meeting','sean'])
    
    # ═══ 7. KEY DIRECTIVES ═══
    print('\n⚡ KEY DIRECTIVES')
    directive_file = os.path.join(WORKSPACE, 'memory/2026-03-17-sean-directive-team-meeting.md')
    if os.path.exists(directive_file):
        upload_file(directive_file, 'directive', 10, ['sean','directive','acti-forge','cia','creative-forge'])

    # ═══ SUMMARY ═══
    print(f'\n{"="*60}')
    print(f'🏠 CONTINUITY UPLOAD COMPLETE')
    print(f'   ✅ Uploaded: {stats["uploaded"]}')
    print(f'   ❌ Failed: {stats["failed"]}')
    print(f'   ⏭️  Skipped: {stats["skipped"]}')
    print(f'   Namespace: {NAMESPACE}')
    print(f'{"="*60}')

if __name__ == '__main__':
    main()
