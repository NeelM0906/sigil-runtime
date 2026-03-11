#!/usr/bin/env python3
"""
Pinecone Knowledge Base Query Tool
Queries Pinecone indexes using OpenAI embeddings.
Usage:
  python3 pinecone_query.py --index <index_name> --query "your question"
  python3 pinecone_query.py --index <index_name> --list-namespaces
  python3 pinecone_query.py --index <index_name> --query "..." --api-key-env PINECONE_API_KEY_STRATA
"""

import argparse
import json
import os
import sys

# Resolve .venv relative to the shared ~/.openclaw root, regardless of current user HOME.
OPENCLAW_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_PYTHON = os.path.join(OPENCLAW_DIR, ".venv", "bin", "python")
VENV_DIR = os.path.dirname(os.path.dirname(VENV_PYTHON))
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.prefix) != os.path.realpath(VENV_DIR):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

try:
    from pinecone import Pinecone
    import urllib.request
except ImportError:
    print("Missing dependencies. Run: ~/.openclaw/.venv/bin/pip install openai pinecone requests")
    sys.exit(1)


def load_env_file(path):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            values[key.strip()] = val
    return values


def get_embedding(text, openai_api_key, model="text-embedding-3-small"):
    """Get embedding from OpenAI API."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = json.dumps({"input": text, "model": model}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result["data"][0]["embedding"]


def query_pinecone(index_name, query_text, pinecone_api_key, openai_api_key, namespace=None, top_k=5):
    """Query a Pinecone index with a text query."""
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)

    # Get embedding for query
    embedding = get_embedding(query_text, openai_api_key=openai_api_key)

    # Query Pinecone
    kwargs = {
        "vector": embedding,
        "top_k": top_k,
        "include_metadata": True
    }
    if namespace:
        kwargs["namespace"] = namespace
    
    results = index.query(**kwargs)
    return results

def main():
    parser = argparse.ArgumentParser(description="Query Pinecone knowledge base")
    parser.add_argument("--index", required=True, help="Pinecone index name")
    parser.add_argument("--query", help="Query text")
    parser.add_argument("--namespace", default=None, help="Namespace to query")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results")
    parser.add_argument(
        "--api-key-env",
        default="PINECONE_API_KEY",
        help="Environment variable name for the Pinecone API key (default: PINECONE_API_KEY)"
    )
    parser.add_argument(
        "--openai-key-env",
        default="OPENROUTER_API_KEY",
        help="Environment variable name for the OpenAI API key (default: OPENAI_API_KEY)"
    )
    parser.add_argument("--list-namespaces", action="store_true", help="List namespaces in the index")
    args = parser.parse_args()

    env_file_values = load_env_file(os.path.expanduser("~/.openclaw/.env"))
    pinecone_api_key = os.environ.get(args.api_key_env) or env_file_values.get(args.api_key_env)
    openai_api_key = os.environ.get(args.openai_key_env) or env_file_values.get(args.openai_key_env)

    if not pinecone_api_key:
        print(f"ERROR: Missing Pinecone key '{args.api_key_env}' (env var or ~/.openclaw/.env)")
        sys.exit(1)

    if not args.list_namespaces and not args.query:
        print("ERROR: --query is required unless --list-namespaces is set")
        sys.exit(1)

    if not args.list_namespaces and not openai_api_key:
        print(f"ERROR: Missing API key '{args.openai_key_env}' (env var or ~/.openclaw/.env)")
        sys.exit(1)

    if args.list_namespaces:
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index(args.index)
        stats = index.describe_index_stats()
        print(f"\nNamespaces in '{args.index}':")
        for ns, ns_stats in (stats.namespaces or {}).items():
            ns_display = ns if ns else "(default)"
            vector_count = getattr(ns_stats, "vector_count", None)
            if vector_count is None and isinstance(ns_stats, dict):
                vector_count = ns_stats.get("vector_count")
            print(f"  {ns_display}: {vector_count if vector_count is not None else '?'} vectors")
        return

    results = query_pinecone(
        args.index,
        args.query,
        pinecone_api_key=pinecone_api_key,
        openai_api_key=openai_api_key,
        namespace=args.namespace,
        top_k=args.top_k
    )

    print(f"\n🔍 Query: \"{args.query}\"")
    key_label = args.api_key_env
    print(
        f"📂 Index: {args.index}"
        + (f" | Namespace: {args.namespace}" if args.namespace else "")
        + f" | Key: {key_label}"
    )
    print(f"📊 Results: {len(results.matches)}\n")

    for i, match in enumerate(results.matches, 1):
        score = match.score
        metadata = match.metadata if match.metadata else {}
        print(f"--- Result {i} (score: {score:.4f}) ---")
        for key, value in metadata.items():
            # Truncate long values for display
            val_str = str(value)
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            print(f"  {key}: {val_str}")
        print()

if __name__ == "__main__":
    main()
