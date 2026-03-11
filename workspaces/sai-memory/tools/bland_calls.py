#!/usr/bin/env python3
"""
Bland.ai call explorer for quick mission analysis.

Examples:
  python3 tools/bland_calls.py --limit 50 --today --show-pathways
  python3 tools/bland_calls.py --limit 100 --today --top 15
  python3 tools/bland_calls.py --pathway-id <PATHWAY_ID> --top 10
  python3 tools/bland_calls.py --details <CALL_ID>
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

OPENCLAW_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_PYTHON = os.path.join(OPENCLAW_DIR, ".venv", "bin", "python")
VENV_DIR = os.path.dirname(os.path.dirname(VENV_PYTHON))
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.prefix) != os.path.realpath(VENV_DIR):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import requests


API_BASE = "https://api.bland.ai/v1"


def load_env_file(path):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val
    return values


def resolve_bland_key():
    env_key = os.environ.get("BLAND_API_KEY")
    if env_key:
        return env_key
    dot_env = load_env_file(os.path.expanduser("~/.openclaw/.env"))
    return dot_env.get("BLAND_API_KEY")


def iso_to_dt(value):
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def api_get(path, bland_key, params=None):
    url = f"{API_BASE}{path}"
    resp = requests.get(
        url,
        params=params or {},
        headers={"authorization": bland_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def print_row(call):
    cid = call.get("c_id") or call.get("call_id") or "unknown"
    created = call.get("created_at", "")
    mins = call.get("call_length", 0) or 0
    to = str(call.get("to", "") or "")
    pathway_id = str(call.get("pathway_id", "") or "")
    status = str(call.get("status", "") or "")
    queue_status = str(call.get("queue_status", "") or "")
    print(
        f"{cid[:8]}  {created[:19]:19}  {mins:6.2f}m  "
        f"{to:15}  {pathway_id[:8]:8}  {status:9}  {queue_status}"
    )


def main():
    parser = argparse.ArgumentParser(description="Inspect Bland.ai call records")
    parser.add_argument("--limit", type=int, default=50, help="Calls to request (default: 50)")
    parser.add_argument("--pathway-id", help="Filter results to one pathway ID")
    parser.add_argument("--today", action="store_true", help="Only include calls from today (UTC)")
    parser.add_argument("--top", type=int, default=10, help="Top calls to display by call_length (default: 10)")
    parser.add_argument("--show-pathways", action="store_true", help="Show pathway counts")
    parser.add_argument("--details", help="Fetch full details for a specific call_id/c_id")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output")
    args = parser.parse_args()

    bland_key = resolve_bland_key()
    if not bland_key:
        print("ERROR: BLAND_API_KEY not found in env or ~/.openclaw/.env")
        sys.exit(1)

    if args.details:
        detail = api_get(f"/calls/{args.details}", bland_key=bland_key)
        if args.json:
            print(json.dumps(detail, indent=2))
            return
        print(f"Call: {detail.get('c_id') or detail.get('call_id')}")
        print(f"Created: {detail.get('created_at')}")
        print(f"Pathway ID: {detail.get('pathway_id')}")
        print(f"Duration: {detail.get('call_length')} min")
        print(f"Status: {detail.get('status')} / {detail.get('queue_status')}")
        print(f"To: {detail.get('to')}  From: {detail.get('from')}")
        transcript = detail.get("concatenated_transcript") or ""
        if transcript:
            preview = transcript[:1500]
            print("\nTranscript preview:")
            print(preview + ("..." if len(transcript) > 1500 else ""))
        return

    payload = api_get("/calls", bland_key=bland_key, params={"limit": args.limit})
    calls = payload.get("calls", [])
    if args.pathway_id:
        calls = [c for c in calls if c.get("pathway_id") == args.pathway_id]
    if args.today:
        today_utc = datetime.now(timezone.utc).date()
        filtered = []
        for c in calls:
            dt = iso_to_dt(c.get("created_at"))
            if dt and dt.astimezone(timezone.utc).date() == today_utc:
                filtered.append(c)
        calls = filtered

    if args.json:
        print(json.dumps(calls, indent=2))
        return

    print(f"Fetched: {len(payload.get('calls', []))} / total {payload.get('total_count', '?')}")
    print(f"Filtered: {len(calls)}")
    if not calls:
        return

    if args.show_pathways:
        pathway_counts = Counter(c.get("pathway_id", "unknown") for c in calls)
        print("\nPathway counts:")
        for pathway_id, count in pathway_counts.most_common():
            print(f"  {pathway_id}: {count}")

    ranked = sorted(calls, key=lambda c: float(c.get("call_length") or 0), reverse=True)
    top_n = ranked[: max(1, args.top)]
    print("\nTop calls by duration:")
    print("call_id    created_at            length    to               pathway   status     queue_status")
    for call in top_n:
        print_row(call)


if __name__ == "__main__":
    main()
