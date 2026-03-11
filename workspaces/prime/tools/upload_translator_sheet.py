#!/usr/bin/env python3
"""
Upload Translator Master Sheet (all 143 tabs) to saimemory Pinecone.
Reads CSVs from /tmp/translator-sheets/, chunks rows, embeds, uploads.
"""
import os, sys, json, csv, hashlib, time, requests
from pathlib import Path

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
NAMESPACE = 'translator-master-sheet'

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

def process_tab(gid, csv_path, pc_index):
    """Process a single tab CSV and upload to Pinecone."""
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = []
        for row in reader:
            if row and any(cell.strip() for cell in row[:5]):
                rows.append(row)

    if not rows:
        return 0

    # Get first topic for metadata
    first_topic = rows[0][0][:200] if rows[0][0] else "(unknown)"

    # Chunk rows into groups of 3 for embedding (balance between granularity and API calls)
    uploaded = 0
    chunk_size = 3

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]

        # Build text from all 5 columns for each row in chunk
        text_parts = []
        for row in chunk:
            topic = row[0] if len(row) > 0 else ""
            context = row[1][:2000] if len(row) > 1 else ""
            formula = row[2][:2000] if len(row) > 2 else ""
            lesson = row[3][:1500] if len(row) > 3 else ""
            condition = row[4][:1500] if len(row) > 4 else ""
            text_parts.append(f"TOPIC: {topic}\nCONTEXT: {context}\nFORMULA: {formula}\nLESSON: {lesson}\nCONDITION: {condition}")

        full_text = "\n\n---\n\n".join(text_parts)

        embedding = embed_text(full_text)
        if not embedding:
            continue

        vid = hashlib.md5(f"{gid}-{i}".encode()).hexdigest()[:16]

        pc_index.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': full_text[:40000],
                'gid': str(gid),
                'first_topic': first_topic[:200],
                'chunk_start': i,
                'chunk_end': min(i + chunk_size, len(rows)),
                'total_rows': len(rows),
                'type': 'translator-sheet',
                'source': 'translator-master-sheet',
            }
        }], namespace=NAMESPACE)

        uploaded += 1
        time.sleep(0.2)  # Rate limit

    return uploaded

def main():
    csv_dir = Path('/tmp/translator-sheets')
    catalog_path = Path('/tmp/sheet_catalog.json')

    if not catalog_path.exists():
        print("ERROR: No catalog found. Run the sheet scanner first.")
        return

    with open(catalog_path) as f:
        catalog = json.load(f)

    # Sort by rows descending (biggest/most important first)
    catalog.sort(key=lambda x: x['rows'], reverse=True)

    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('saimemory')

    total_vectors = 0
    total_tabs = 0

    for entry in catalog:
        gid = entry['gid']
        rows = entry['rows']
        first = entry.get('first_topic', '')[:60]

        if rows == 0:
            continue

        csv_path = csv_dir / f"tab_{gid}.csv"
        if not csv_path.exists():
            print(f"  SKIP gid={gid}: CSV not found")
            continue

        print(f"Tab gid={gid} ({rows} rows): {first}...")
        vectors = process_tab(gid, csv_path, idx)
        total_vectors += vectors
        total_tabs += 1
        print(f"  → {vectors} vectors uploaded")

        if total_tabs % 10 == 0:
            print(f"  --- Progress: {total_tabs} tabs, {total_vectors} vectors ---")

    print(f"\n{'='*60}")
    print(f"COMPLETE: {total_vectors} vectors from {total_tabs} tabs → saimemory/{NAMESPACE}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
