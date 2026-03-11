#!/usr/bin/env python3
"""
Context Fetch — Unified knowledge retrieval for all ACT-I beings and sub-agents.

Queries Pinecone (saimemory + ublib2) and Supabase in ONE call.
Returns a compact context block — just what the caller needs, no bloat.

Usage:
  python3 tools/context_fetch.py --topic "dual scoring writer being"
  python3 tools/context_fetch.py --topic "NJ PI attorneys" --max-chars 8000
  python3 tools/context_fetch.py --topic "Sean's directives" --index saimemory --top-k 10
  python3 tools/context_fetch.py --topic "zone actions" --include-postgres
  python3 tools/context_fetch.py --topic "Formula Judge" --indexes saimemory,ublib2
  python3 tools/context_fetch.py --list-indexes

  ## DEEP GROUNDING MODE (The Translator Standard)
  python3 tools/context_fetch.py --topic "fear selection self mastery" --deep
  python3 tools/context_fetch.py --topic "agreement formation" --deep --max-chars 15000

  --deep queries 25 results per index across saimemory, ublib2, acti-judges, AND
  ultimatestratabrain = 100+ chunks of grounding before producing any output.
  This is the TRANSLATOR STANDARD. Kai reads 100+ chunks. So should we.

Every sister. Every baby. Every contractor. This is how you get grounded.
"""

import argparse
import json
import os
import sys

# Resolve .venv
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
VENV_DIR = os.path.dirname(os.path.dirname(VENV_PYTHON))
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.prefix) != os.path.realpath(VENV_DIR):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

try:
    from pinecone import Pinecone
    import requests
except ImportError:
    print("ERROR: Missing deps. Run: tools/.venv/bin/pip install pinecone openai requests supabase")
    sys.exit(1)


def load_env():
    """Load env vars from ~/.openclaw/.env"""
    env_path = os.path.join(os.path.expanduser("~"), ".openclaw", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())


def get_embedding(text):
    """Get embedding via OpenRouter (preferred) or raise."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    resp = requests.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "openai/text-embedding-3-small", "input": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def query_pinecone(index_name, embedding, top_k=5, api_key_env="PINECONE_API_KEY", fan_out_namespaces=False):
    """Query a Pinecone index, return matches.
    
    If fan_out_namespaces=True, query all namespaces and merge results.
    This is needed for indexes like acti-judges and ultimatestratabrain
    that store vectors in namespaces (querying without namespace returns nothing).
    """
    api_key = os.environ.get(api_key_env)
    if not api_key:
        return []
    try:
        pc = Pinecone(api_key=api_key)
        idx = pc.Index(index_name)
        
        if not fan_out_namespaces:
            results = idx.query(vector=embedding, top_k=top_k, include_metadata=True)
            return results.get("matches", [])
        
        # Fan out: get all namespaces, query each, merge + sort by score
        stats = idx.describe_index_stats()
        namespaces = list(stats.namespaces.keys())
        if not namespaces:
            return []
        
        all_matches = []
        # Query top namespaces by vector count (skip tiny ones for speed)
        ns_by_size = sorted(namespaces, key=lambda ns: stats.namespaces[ns].vector_count, reverse=True)
        # In deep mode, query more namespaces; otherwise limit to top 10
        max_ns = min(len(ns_by_size), 20 if top_k >= 10 else 10)
        per_ns_k = max(3, top_k // max_ns + 1)
        
        for ns in ns_by_size[:max_ns]:
            try:
                results = idx.query(vector=embedding, top_k=per_ns_k, include_metadata=True, namespace=ns)
                for m in results.get("matches", []):
                    m["namespace"] = ns
                    all_matches.append(m)
            except Exception:
                continue
        
        # Sort by score, return top_k
        all_matches.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_matches[:top_k]
    except Exception as e:
        return [{"error": str(e)}]


def query_postgres(topic):
    """Query sai_memory table for relevant entries."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        return []
    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        # Full-text search on content column
        resp = requests.get(
            f"{url}/rest/v1/sai_memory",
            headers=headers,
            params={
                "select": "id,category,content,created_at",
                "content": f"ilike.*{topic[:50]}*",
                "limit": "10",
                "order": "created_at.desc",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []


def format_results(pinecone_results, postgres_results, max_chars, deep=False):
    """Format all results into a compact context block."""
    lines = []
    lines.append("=" * 60)
    if deep:
        lines.append("DEEP CONTEXT INJECTION — Translator-Grade Grounding")
        lines.append("(100+ chunks across 4 indexes + Postgres)")
    else:
        lines.append("CONTEXT INJECTION — Retrieved Knowledge")
    lines.append("=" * 60)

    total_chunks = 0

    if pinecone_results:
        lines.append("")
        lines.append("## PINECONE KNOWLEDGE")
        lines.append("")
        for i, group in enumerate(pinecone_results):
            idx_name = group["index"]
            matches = group["matches"]
            if not matches or (len(matches) == 1 and "error" in matches[0]):
                err = matches[0].get("error", "no results") if matches else "no results"
                lines.append(f"### {idx_name}: {err}")
                continue
            lines.append(f"### {idx_name} ({len(matches)} results)")
            lines.append("")
            for m in matches:
                if "error" in m:
                    lines.append(f"  ERROR: {m['error']}")
                    continue
                score = m.get("score", 0)
                meta = m.get("metadata", {})
                text = meta.get("text", meta.get("content", meta.get("chunk_text", str(meta))))
                source = meta.get("source", "")
                # In deep mode, allow longer chunks for richer context
                max_chunk = 1200 if deep else 800
                if len(text) > max_chunk:
                    text = text[:max_chunk] + "..."
                source_tag = f" | src: {source}" if source else ""
                lines.append(f"  [{score:.3f}{source_tag}] {text}")
                lines.append("")
                total_chunks += 1

    if postgres_results:
        lines.append("")
        lines.append("## POSTGRES KNOWLEDGE")
        lines.append("")
        pg_limit = 10 if deep else 5
        for row in postgres_results[:pg_limit]:
            cat = row.get("category", "?")
            content = str(row.get("content", ""))[:500]
            created = row.get("created_at", "?")[:10]
            lines.append(f"  [{cat} | {created}] {content}")
            lines.append("")
            total_chunks += 1

    if not pinecone_results and not postgres_results:
        lines.append("")
        lines.append("No results found. Try a different topic or broader query.")

    lines.append("=" * 60)
    lines.append(f"Total chunks retrieved: {total_chunks}")
    if deep:
        if total_chunks < 50:
            lines.append("⚠️  WARNING: Deep mode should retrieve 100+ chunks. Consider broader topic or more indexes.")
        else:
            lines.append(f"✅ Deep grounding: {total_chunks} chunks — {'Translator-grade' if total_chunks >= 100 else 'good but not yet Translator-grade (aim for 100+)'}")
    lines.append("=" * 60)

    output = "\n".join(lines)
    if len(output) > max_chars:
        output = output[:max_chars] + "\n... [truncated to max-chars]"
    return output


def list_indexes():
    """List available Pinecone indexes."""
    load_env()
    print("\n=== PRIMARY PINECONE (PINECONE_API_KEY) ===")
    try:
        pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        for idx in pc.list_indexes():
            print(f"  {idx.name} — {idx.dimension}d, {idx.metric}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n=== STRATA PINECONE (PINECONE_API_KEY_STRATA) ===")
    try:
        pc2 = Pinecone(api_key=os.environ.get("PINECONE_API_KEY_STRATA"))
        for idx in pc2.list_indexes():
            print(f"  {idx.name} — {idx.dimension}d, {idx.metric}")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Context Fetch — unified knowledge retrieval for ACT-I beings")
    parser.add_argument("--topic", "-t", help="Topic to query")
    parser.add_argument("--indexes", "-i", default="saimemory,ublib2",
                       help="Comma-separated Pinecone indexes (default: saimemory,ublib2)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Results per index (default: 5)")
    parser.add_argument("--max-chars", "-m", type=int, default=6000, help="Max output chars (default: 6000)")
    parser.add_argument("--include-postgres", "-p", action="store_true", help="Also query Postgres sai_memory")
    parser.add_argument("--list-indexes", action="store_true", help="List all available Pinecone indexes")
    parser.add_argument("--strata", "-s", action="store_true",
                       help="Query from Strata Pinecone (uses PINECONE_API_KEY_STRATA)")
    parser.add_argument("--deep", "-d", action="store_true",
                       help="Deep grounding mode: 25 results × 4 indexes + Postgres = 100+ chunks. "
                            "The Translator standard. Use before any significant output.")
    args = parser.parse_args()

    load_env()

    if args.list_indexes:
        list_indexes()
        return

    if not args.topic:
        parser.error("--topic is required (unless --list-indexes)")

    # DEEP MODE: Override settings to Translator standard
    if args.deep:
        args.indexes = "saimemory,ublib2,acti-judges"
        args.top_k = 25
        args.include_postgres = True
        args.strata = True  # Also hit ultimatestratabrain
        if args.max_chars < 15000:
            args.max_chars = 15000  # Need more space for 100+ chunks

    # Get embedding
    try:
        embedding = get_embedding(args.topic)
    except Exception as e:
        print(f"ERROR getting embedding: {e}")
        sys.exit(1)

    # Query Pinecone indexes
    indexes = [x.strip() for x in args.indexes.split(",")]
    pinecone_results = []

    # Determine which indexes go to which API key
    STRATA_INDEXES = {
        "ultimatestratabrain", "suritrial", "2025selfmastery", "oracleinfluencemastery",
        "nashmacropareto", "rtioutcomes120", "010526calliememory", "miraagentnew-25-07-25",
        "unblindedtranslatorbrain", "boltn8n", "athenan8n", "paladinn8n",
    }

    # Indexes that require namespace fan-out (they store vectors in namespaces only)
    FAN_OUT_INDEXES = {"acti-judges", "ultimatestratabrain"}

    for idx_name in indexes:
        if idx_name in STRATA_INDEXES:
            api_key_env = "PINECONE_API_KEY_STRATA"
        else:
            api_key_env = "PINECONE_API_KEY"

        fan_out = idx_name in FAN_OUT_INDEXES
        matches = query_pinecone(idx_name, embedding, top_k=args.top_k,
                                 api_key_env=api_key_env, fan_out_namespaces=fan_out)
        pinecone_results.append({"index": idx_name, "matches": matches})

    # In deep mode, also query ultimatestratabrain separately if --strata flag
    if args.strata and "ultimatestratabrain" not in indexes:
        strata_matches = query_pinecone(
            "ultimatestratabrain", embedding, top_k=args.top_k,
            api_key_env="PINECONE_API_KEY_STRATA", fan_out_namespaces=True
        )
        pinecone_results.append({"index": "ultimatestratabrain", "matches": strata_matches})

    # Query Postgres
    postgres_results = []
    if args.include_postgres:
        postgres_results = query_postgres(args.topic)

    # Format and print
    output = format_results(pinecone_results, postgres_results, args.max_chars, deep=args.deep)
    print(output)


if __name__ == "__main__":
    main()
