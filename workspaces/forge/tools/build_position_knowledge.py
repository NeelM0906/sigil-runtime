"""
Position-Level Knowledge Base Builder
Generates PhD-level judge + worker knowledge for each of 2,696 positions
Uploads to acti-judges Pinecone with proper namespace + parent_being tags

Usage:
  python3 build_position_knowledge.py [--start N] [--end N] [--cluster NAME]
"""

import json, os, sys, time, argparse, hashlib
from pinecone import Pinecone
from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────────────
HIERARCHY_FILE = "~/.openclaw/workspace-forge/data/hierarchy.json"
LOG_DIR = "~/.openclaw/workspace-forge/reports"
PINECONE_INDEX = "acti-judges"
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "anthropic/claude-haiku-4-5"   # fast + cheap via OpenRouter

# Creature scale for scoring rubrics
CREATURE_SCALE = [
    ("Grain of Sand", "0-10th percentile — no real-world results, purely theoretical"),
    ("Iguana",        "25th percentile — occasional accidental success, 1-3% outputs"),
    ("Komodo",        "50th percentile — consistent but not exceptional, bumps into results"),
    ("Crocodile",     "80th percentile — measurable, repeatable, above-market outputs"),
    ("Godzilla",      "99th percentile — elite, scalable, causes exponential outcomes"),
    ("Bolt",          "99.999th percentile — the ceiling no one has reached yet"),
]

JUDGE_PROMPT = """You are generating a PhD-level knowledge base entry for an ACT-I judge evaluating the position: {title}
Cluster: {cluster} | Family: {family} | Parent Being: {parent_being}
Position description: {description}

Generate a JUDGE SCORING RUBRIC with:
1. What this position is truly responsible for (2-3 sentences, no fluff)
2. The 3-5 most critical skills/outputs that determine mastery
3. Creature Scale scoring thresholds with SPECIFIC numerical evidence:
   - Grain of Sand: what does terrible output look like? (specific numbers/behaviors)
   - Iguana: what does mediocre look like? (specific metrics)
   - Komodo: what does average look like? (specific outputs)
   - Crocodile: what does excellent look like? (specific KPIs, conversion rates, output quality)
   - Godzilla: what does elite output look like? (specific benchmarks, scale, impact)
4. The #1 failure pattern judges must watch for
5. The single best signal that someone is Godzilla-level in this position

Be SPECIFIC. Use real numbers. A judge reading this should know immediately if they're looking at Komodo or Godzilla output.
Filter everything through the Unblinded Formula — influence mastery and Zone Action thinking."""

WORKER_PROMPT = """You are generating a worker execution guide for an ACT-I being operating as: {title}
Cluster: {cluster} | Family: {family} | Parent Being: {parent_being}
Position description: {description}

Generate an OPERATIONAL SOP containing:
1. Core mission (1 sentence — what does success in this role create?)
2. Daily workflow (numbered steps, hour-by-hour if applicable)
3. Decision tree: the 3 most common decision points and how to navigate them
4. Key tools and platforms (specific names, not generic)
5. Output standards — what does a deliverable look like at Crocodile level?
6. Handoff protocols — who receives your output upstream/downstream?
7. The Zone Action — what is the 0.8% of activity that produces 51%+ of results in this role?

Be operational. Be specific. A being reading this should know exactly what to do on Day 1.
Apply the 4-Step Communication Model and Unblinded Formula thinking throughout."""

# ── Helpers ─────────────────────────────────────────────────────────────────
def vec_id(namespace, suffix):
    h = hashlib.md5(f"{namespace}-{suffix}".encode()).hexdigest()[:8]
    return f"{namespace}-{suffix}-{h}"

def get_embedding(client_embed, text):
    resp = client_embed.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding

def generate_content(client_chat, prompt):
    resp = client_chat.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.7
    )
    return resp.choices[0].message.content

def namespace_from_cluster(cluster_name):
    """Map cluster name to existing acti-judges namespace (depth not width)."""
    return cluster_name.lower().replace(" ", "-").replace("&", "and").replace("/", "-").replace("(","").replace(")","")

def namespace_from_position(position_id, cluster_name):
    """Use the existing cluster namespace — inject position vectors INTO it."""
    return namespace_from_cluster(cluster_name)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--cluster", type=str, default=None, help="Run only this cluster name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Init clients
    openrouter_key = os.environ["OPENROUTER_API_KEY"]
    pinecone_key = os.environ["PINECONE_API_KEY"]

    client_chat = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
    client_embed = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index(PINECONE_INDEX)

    # Load hierarchy
    with open(HIERARCHY_FILE) as f:
        data = json.load(f)

    # Flatten all positions
    all_positions = []
    for family in data.get("families", []):
        for being in family.get("beings", []):
            for pos in being.get("fullPositions", []):
                all_positions.append({
                    "id": pos.get("id") or f"gen-{hashlib.md5(pos['title'].encode()).hexdigest()[:8]}",
                    "title": pos["title"],
                    "description": pos.get("description", ""),
                    "cluster": being["name"],
                    "family": family["name"],
                    "parent_being": being.get("kaiBeing", being["name"]),
                    "craft": being.get("craft", ""),
                })

    # Filter by cluster if specified
    if args.cluster:
        all_positions = [p for p in all_positions if p["cluster"].lower() == args.cluster.lower()]
        print(f"Filtered to cluster '{args.cluster}': {len(all_positions)} positions")

    # Slice range
    subset = all_positions[args.start:args.end]
    total = len(subset)

    print(f"\n⚔️ Position Knowledge Base Builder")
    print(f"   {total} positions to process (of {len(all_positions)} total)")
    print(f"   Dry run: {args.dry_run}\n")

    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = f"{LOG_DIR}/position-kb-{int(time.time())}.log"
    errors = []

    for i, pos in enumerate(subset, 1):
        ns = namespace_from_position(pos["id"], pos["cluster"])
        print(f"[{i}/{total}] {pos['title']} ({pos['cluster']}) → ns:{ns}")

        if args.dry_run:
            continue

        try:
            # Generate judge rubric
            judge_content = generate_content(client_chat, JUDGE_PROMPT.format(**pos))
            time.sleep(0.5)

            # Generate worker SOP
            worker_content = generate_content(client_chat, WORKER_PROMPT.format(**pos))
            time.sleep(0.5)

            # Embed both
            judge_vec = get_embedding(client_embed, judge_content)
            worker_vec = get_embedding(client_embed, worker_content)

            if not args.dry_run:
                # Upload to Pinecone
                index.upsert(
                    vectors=[
                        {
                            "id": vec_id(ns, "judge_rubric"),
                            "values": judge_vec,
                            "metadata": {
                                "position_id": pos["id"],
                                "title": pos["title"],
                                "cluster": pos["cluster"],
                                "family": pos["family"],
                                "parent_being": pos["parent_being"],
                                "section": "judge_rubric",
                                "type": "judge_rubric",
                                "source": "position_kb_builder",
                                "text": judge_content[:2000],
                            }
                        },
                        {
                            "id": vec_id(ns, "worker_sop"),
                            "values": worker_vec,
                            "metadata": {
                                "position_id": pos["id"],
                                "title": pos["title"],
                                "cluster": pos["cluster"],
                                "family": pos["family"],
                                "parent_being": pos["parent_being"],
                                "section": "worker_sop",
                                "type": "worker_sop",
                                "source": "position_kb_builder",
                                "text": worker_content[:2000],
                            }
                        }
                    ],
                    namespace=ns
                )
                print(f"   ✅ Uploaded judge_rubric + worker_sop → {ns}")

            # Log
            with open(log_file, "a") as lf:
                lf.write(f"[{i}/{total}] OK {pos['title']} → {ns}\n")

        except Exception as e:
            err = f"[{i}/{total}] ERROR {pos['title']}: {e}"
            print(f"   ❌ {err}")
            errors.append(err)
            with open(log_file, "a") as lf:
                lf.write(err + "\n")
            time.sleep(2)

        # Rate limit breathing room
        if i % 50 == 0:
            stats = index.describe_index_stats()
            print(f"\n   📊 Pinecone total vectors: {stats['total_vector_count']}\n")

    print(f"\n✅ Done. {total - len(errors)} successful, {len(errors)} errors.")
    print(f"   Log: {log_file}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
