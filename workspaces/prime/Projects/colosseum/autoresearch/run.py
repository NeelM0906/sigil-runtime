#!/usr/bin/env python3
"""
🔥 AUTORESEARCH RUNNER — Patches env + launches engine.
Fixes: OpenRouter API, scenario dict loading.
"""
import os, sys, json

# --- Fix 1: Set OpenRouter as OpenAI-compatible endpoint ---
env_path = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Map OpenRouter key to OpenAI env vars
or_key = os.environ.get("OPENROUTER_API_KEY", "")
if or_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = or_key
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

# Use good models via OpenRouter
os.environ.setdefault("AUTORESEARCH_BEING_MODEL", "anthropic/claude-sonnet-4")
os.environ.setdefault("AUTORESEARCH_JUDGE_MODEL", "openai/gpt-4o")
os.environ.setdefault("AUTORESEARCH_ANALYST_MODEL", "openai/gpt-4o")

# --- Fix 2: Monkey-patch scenario loading for dict-keyed JSON ---
import engine

_orig_load = engine.load_default_scenarios

def patched_load_scenarios():
    """Load scenarios from dict-keyed expanded JSON."""
    from pathlib import Path
    scenarios_path = engine.COLOSSEUM_DIR / "v2" / "data" / "scenarios_expanded.json"
    if scenarios_path.exists():
        try:
            with open(scenarios_path) as f:
                raw = json.load(f)
            scenarios = []
            for key, s in raw.items():
                if key.startswith("_"):
                    continue  # skip _meta
                person = s.get("person", {})
                if isinstance(person, dict):
                    person_str = f"{person.get('name','')}, {person.get('role','')}. Concern: {person.get('concern','')}. Hot button: {person.get('hot_button','')}"
                else:
                    person_str = str(person)
                scenarios.append(engine.Scenario(
                    id=key,
                    situation=s.get("situation", s.get("title", "")),
                    person=person_str,
                    challenge=s.get("success_criteria", s.get("challenge", "")),
                    difficulty=s.get("difficulty", "gold"),
                    category=s.get("category", "influence"),
                ))
                if len(scenarios) >= 50:
                    break
            if scenarios:
                print(f"📂 Loaded {len(scenarios)} scenarios from expanded JSON")
                return scenarios
        except Exception as e:
            print(f"⚠ Scenario load error: {e}")
    return _orig_load()

engine.load_default_scenarios = patched_load_scenarios

# --- Launch ---
if __name__ == "__main__":
    sys.argv[0] = "engine.py"  # cosmetic
    engine.main()
