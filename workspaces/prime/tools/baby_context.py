#!/usr/bin/env python3
"""Baby Context API — Smart context budgeting for sub-agents.

Instead of babies reading 200KB of flat files, they call this once
and get exactly the context they need, budgeted to a target size.

Usage:
    # From a baby's task prompt:
    cd ~/.openclaw/workspace/tools && .venv/bin/python3 baby_context.py --topic "colosseum scoring" --budget 4000

    # With specific sources:
    .venv/bin/python3 baby_context.py --topic "writer being scenarios" --budget 6000 --sources pinecone,postgres,files

    # Just Postgres structured data:
    .venv/bin/python3 baby_context.py --topic "current zone actions" --budget 3000 --sources postgres

    # Everything (for complex tasks):
    .venv/bin/python3 baby_context.py --topic "full colosseum architecture" --budget 8000 --sources all

Output: A single text block, budgeted to --budget chars, ready to inject into a prompt.
"""

import os, sys, json, argparse, urllib.request
from pathlib import Path

WORKSPACE = os.path.join(os.environ.get("HOME", ""), ".openclaw", "workspace")


def query_pinecone(topic, api_key, openrouter_key, top_k=5, indexes=None):
    """Query Pinecone indexes for relevant context."""
    if not indexes:
        indexes = ["saimemory", "ublib2"]

    # Get embedding
    data = json.dumps({"input": topic[:2000], "model": "openai/text-embedding-3-small"}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/embeddings",
        data=data,
        headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=20)
    embedding = json.loads(resp.read())["data"][0]["embedding"]

    hosts = {
        "saimemory": "saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io",
        "ublib2": "ublib2-hw65sks.svc.aped-4627-b74a.pinecone.io",
        "acti-judges": "acti-judges-hw65sks.svc.aped-4627-b74a.pinecone.io",
    }

    results = []
    for idx_name in indexes:
        host = hosts.get(idx_name)
        if not host:
            continue
        body = json.dumps({"vector": embedding, "topK": top_k, "includeMetadata": True}).encode()
        req = urllib.request.Request(
            f"https://{host}/query",
            data=body,
            headers={"Api-Key": api_key, "Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            for m in data.get("matches", []):
                text = m.get("metadata", {}).get("text", "") or m.get("metadata", {}).get("content", "")
                if text and m.get("score", 0) > 0.3:
                    results.append({"score": m["score"], "text": text[:600], "source": idx_name})
        except Exception as e:
            pass

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def query_postgres(topic, supabase_url, supabase_key):
    """Query Postgres for structured data relevant to the topic."""
    results = []

    # Query sai_memory for relevant memories
    topic_words = topic.lower().split()
    for word in topic_words[:3]:
        url = f"{supabase_url}/rest/v1/sai_memory?content=ilike.*{word}*&limit=3&order=created_at.desc"
        req = urllib.request.Request(
            url,
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            for row in data:
                content = row.get("content", "")
                if content:
                    results.append({"text": content[:400], "source": "postgres/sai_memory"})
        except:
            pass

    # Query recent conversations for context
    url = f"{supabase_url}/rest/v1/sai_conversations?order=created_at.desc&limit=5"
    req = urllib.request.Request(
        url,
        headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        for row in data:
            content = row.get("content", "")
            speaker = row.get("speaker", "?")
            if content:
                results.append({"text": f"[{speaker}] {content[:300]}", "source": "postgres/sai_conversations"})
    except:
        pass

    return results


def read_key_files(topic, budget_per_file=1500):
    """Read essential workspace files, truncated to budget."""
    results = []

    # Always include current zone actions (trimmed)
    za_path = os.path.join(WORKSPACE, "ZONE_ACTIONS.md")
    if os.path.exists(za_path):
        with open(za_path) as f:
            content = f.read()
        # Extract just the execution order section
        exec_start = content.find("EXECUTION ORDER")
        if exec_start > 0:
            results.append({"text": content[exec_start:exec_start + budget_per_file], "source": "ZONE_ACTIONS.md"})
        else:
            results.append({"text": content[:budget_per_file], "source": "ZONE_ACTIONS.md"})

    # Today's memory
    from datetime import date
    today = date.today().isoformat()
    mem_path = os.path.join(WORKSPACE, "memory", f"{today}.md")
    if os.path.exists(mem_path):
        with open(mem_path) as f:
            results.append({"text": f.read()[:budget_per_file], "source": f"memory/{today}.md"})

    # CONTINUITY.md hard rules section only
    cont_path = os.path.join(WORKSPACE, "CONTINUITY.md")
    if os.path.exists(cont_path):
        with open(cont_path) as f:
            content = f.read()
        rules_start = content.find("Hard Rules")
        if rules_start > 0:
            results.append({"text": content[rules_start:rules_start + 800], "source": "CONTINUITY.md (rules)"})

    return results


def build_context(topic, budget=4000, sources=None):
    """Build a budget-constrained context packet for a baby."""
    if sources is None:
        sources = ["pinecone", "postgres", "files"]
    elif sources == ["all"]:
        sources = ["pinecone", "postgres", "files"]

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    pinecone_key = os.environ.get("PINECONE_API_KEY", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    all_chunks = []

    # 1. Pinecone (highest signal)
    if "pinecone" in sources and openrouter_key and pinecone_key:
        pc_results = query_pinecone(topic, pinecone_key, openrouter_key, top_k=4)
        for r in pc_results:
            all_chunks.append({"text": r["text"], "source": r["source"], "priority": r["score"]})

    # 2. Postgres (structured data)
    if "postgres" in sources and supabase_url and supabase_key:
        pg_results = query_postgres(topic, supabase_url, supabase_key)
        for r in pg_results:
            all_chunks.append({"text": r["text"], "source": r["source"], "priority": 0.5})

    # 3. Key files (essential workspace context)
    if "files" in sources:
        file_results = read_key_files(topic)
        for r in file_results:
            all_chunks.append({"text": r["text"], "source": r["source"], "priority": 0.4})

    # Sort by priority (highest first)
    all_chunks.sort(key=lambda x: x["priority"], reverse=True)

    # Build output within budget
    output = f"## CONTEXT FOR: {topic}\n\n"
    chars_used = len(output)

    for chunk in all_chunks:
        entry = f"[{chunk['source']}] {chunk['text']}\n\n"
        if chars_used + len(entry) > budget:
            # Truncate last entry to fit
            remaining = budget - chars_used - 50
            if remaining > 100:
                output += f"[{chunk['source']}] {chunk['text'][:remaining]}...\n\n"
            break
        output += entry
        chars_used += len(entry)

    output += f"---\n_Context budget: {chars_used}/{budget} chars | {len(all_chunks)} sources queried_"
    return output


def main():
    parser = argparse.ArgumentParser(description="Baby Context API")
    parser.add_argument("--topic", required=True, help="What the baby needs context about")
    parser.add_argument("--budget", type=int, default=4000, help="Max chars to return (default 4000)")
    parser.add_argument("--sources", default="pinecone,postgres,files", help="Comma-separated: pinecone,postgres,files,all")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of text")
    args = parser.parse_args()

    sources = args.sources.split(",")
    context = build_context(args.topic, budget=args.budget, sources=sources)

    if args.json:
        print(json.dumps({"context": context, "budget": args.budget, "topic": args.topic}))
    else:
        print(context)


if __name__ == "__main__":
    main()
