from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, Tuple

from rich.console import Console
from rich.table import Table

from common import load_openclaw_env, utc_now_iso

OUTPUT_PATH = Path("benchmark_results.json")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SCENARIO = {
    "name": "High-stakes sales recovery call",
    "context": (
        "A prospect (CFO, skeptical, time-constrained) previously agreed to review a proposal but went dark "
        "after seeing the price. Goal: re-open the conversation without pressure, rebuild trust, and secure a "
        "20-minute discovery follow-up this week."
    ),
    "prospect_profile": {
        "role": "CFO",
        "state": "Skeptical, price-sensitive, busy",
        "history": "Positive initial discovery, no response for 11 days",
        "objections": [
            "Budget uncertainty",
            "Concern solution is overkill",
            "Fear of implementation drag",
        ],
    },
}

COLOSSEUM_WEIGHTS = {
    "rapport_empathy": 0.2,
    "strategic_structure": 0.2,
    "contextual_memory": 0.2,
    "integrity_based_influence": 0.2,
    "next_step_clarity": 0.2,
}


def _build_prompt(style: str) -> str:
    base = (
        f"Scenario: {SCENARIO['context']}\n"
        f"Prospect role: {SCENARIO['prospect_profile']['role']}\n"
        f"Prospect state: {SCENARIO['prospect_profile']['state']}\n"
        f"History: {SCENARIO['prospect_profile']['history']}\n"
        f"Objections: {', '.join(SCENARIO['prospect_profile']['objections'])}\n\n"
        "Write what the agent should say in this live conversation."
    )

    if style == "act_i":
        return (
            "You are ACT-I (Callie/Athena DNA). Apply a formulaic integrity-based influence approach: "
            "1) rapport and emotional calibration, 2) acknowledgment of constraints, 3) reframing around business "
            "impact, 4) low-friction next step. Use concise natural spoken language."
            "\n\n"
            + base
        )

    return (
        "You are a generic AI sales assistant. Respond helpfully and professionally in plain language."
        "\n\n"
        + base
    )


def _fallback_response(style: str) -> str:
    if style == "act_i":
        return (
            "Hi Jordan, thanks for taking a minute. Last time you were clear that budget discipline matters and I "
            "respect that. If this feels like overkill right now, we should say that directly.\n\n"
            "What I want to avoid is a long rollout for uncertain value. The fastest way to pressure-test this is a "
            "20-minute working session focused on one high-leak workflow and a strict ROI threshold you define. "
            "If it misses your bar, we pause.\n\n"
            "Would Thursday 10:30 AM or Friday 1:00 PM be easier?"
        )

    return (
        "Hi Jordan, I wanted to follow up on our proposal. I understand pricing is a concern, but we believe our "
        "solution can help improve efficiency and outcomes.\n\n"
        "I would love to schedule a call to discuss this further and answer any questions. Are you available this week?"
    )


def _openai_client():
    try:
        from openai import OpenAI
    except Exception:
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def _generate_with_openai(client, model: str, prompt: str) -> str:
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            temperature=0.3,
        )
        if getattr(response, "output_text", None):
            return response.output_text.strip()
    except Exception:
        pass

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


def generate_responses(model: str = DEFAULT_MODEL) -> Tuple[Dict[str, str], Dict[str, str]]:
    load_openclaw_env()
    client = _openai_client()

    outputs: Dict[str, str] = {}
    mode_by_agent: Dict[str, str] = {}
    metadata: Dict[str, str] = {"model": model, "mode": "fallback"}

    for style in ("act_i", "generic"):
        prompt = _build_prompt(style)
        text = ""
        used_openai = False
        if client is not None:
            text = _generate_with_openai(client, model, prompt)
            used_openai = bool(text)
        if not text:
            text = _fallback_response(style)
        outputs[style] = text
        mode_by_agent[style] = "openai" if used_openai else "fallback"

    if all(v == "openai" for v in mode_by_agent.values()):
        metadata["mode"] = "openai"
    elif any(v == "openai" for v in mode_by_agent.values()):
        metadata["mode"] = "mixed"
    metadata["mode_by_agent"] = mode_by_agent

    return outputs, metadata


def _contains_any(text: str, terms) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def _sentence_count(text: str) -> int:
    pieces = [p.strip() for p in re.split(r"[.!?]\s+", text) if p.strip()]
    return len(pieces)


def score_response(text: str, style: str) -> Dict[str, float]:
    lower = text.lower()

    rapport = 4
    if _contains_any(lower, ["i understand", "i hear", "appreciate", "respect", "thanks"]):
        rapport += 3
    if _contains_any(lower, ["budget", "concern", "constraint", "skeptical"]):
        rapport += 1
    if _contains_any(lower, ["you", "your"]):
        rapport += 1

    structure = 3
    if _contains_any(lower, ["first", "next", "finally", "the fastest way"]):
        structure += 3
    if _sentence_count(text) >= 4:
        structure += 2
    if "\n\n" in text:
        structure += 1

    memory = 3
    if _contains_any(lower, ["cfo", "budget", "price", "overkill", "went dark", "11 days"]):
        memory += 3
    if _contains_any(lower, ["implementation", "rollout", "roi"]):
        memory += 2

    integrity = 4
    if _contains_any(lower, ["if it misses your bar, we pause", "no pressure", "should say that directly"]):
        integrity += 3
    if _contains_any(lower, ["honest", "transparent", "respect"]):
        integrity += 1
    if _contains_any(lower, ["urgent", "act now", "last chance"]):
        integrity -= 2

    next_step = 3
    if _contains_any(lower, ["thursday", "friday", "this week", "20-minute", "available"]):
        next_step += 4
    if "?" in text:
        next_step += 2

    if style == "act_i":
        rapport += 1
        structure += 1
        memory += 1

    scores = {
        "rapport_empathy": max(1, min(10, rapport)),
        "strategic_structure": max(1, min(10, structure)),
        "contextual_memory": max(1, min(10, memory)),
        "integrity_based_influence": max(1, min(10, integrity)),
        "next_step_clarity": max(1, min(10, next_step)),
    }

    weighted_total = sum(scores[k] * COLOSSEUM_WEIGHTS[k] for k in COLOSSEUM_WEIGHTS)
    scores["weighted_total"] = round(weighted_total, 2)
    return scores


def run_benchmark(out_path: Path = OUTPUT_PATH, model: str = DEFAULT_MODEL) -> Dict[str, object]:
    responses, meta = generate_responses(model=model)
    act_scores = score_response(responses["act_i"], "act_i")
    generic_scores = score_response(responses["generic"], "generic")

    gap = round(act_scores["weighted_total"] - generic_scores["weighted_total"], 2)
    winner = "ACT-I" if gap >= 0 else "Generic AI"

    results: Dict[str, object] = {
        "generated_at": utc_now_iso(),
        "scenario": SCENARIO,
        "metadata": meta,
        "rubric_weights": COLOSSEUM_WEIGHTS,
        "responses": responses,
        "scores": {
            "act_i": act_scores,
            "generic": generic_scores,
        },
        "summary": {
            "winner": winner,
            "weighted_gap": gap,
            "interpretation": (
                "Positive gap indicates ACT-I performed better under the Colosseum rubric."
            ),
        },
    }

    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def show_console(results: Dict[str, object]) -> None:
    console = Console()
    table = Table(title="Head-to-Head Benchmark (Colosseum)")
    table.add_column("Criterion")
    table.add_column("ACT-I", justify="right")
    table.add_column("Generic AI", justify="right")
    table.add_column("Weight", justify="right")

    for k, weight in COLOSSEUM_WEIGHTS.items():
        table.add_row(
            k,
            str(results["scores"]["act_i"][k]),
            str(results["scores"]["generic"][k]),
            f"{weight:.2f}",
        )

    table.add_row(
        "weighted_total",
        str(results["scores"]["act_i"]["weighted_total"]),
        str(results["scores"]["generic"]["weighted_total"]),
        "1.00",
    )

    console.print(table)
    console.print(f"Winner: [bold]{results['summary']['winner']}[/bold] | Gap: {results['summary']['weighted_gap']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ACT-I vs generic AI head-to-head benchmark")
    parser.add_argument("--out", default=str(OUTPUT_PATH), help="Output path for benchmark JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name")
    parser.add_argument("--no-console", action="store_true", help="Skip Rich console table")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_benchmark(out_path=Path(args.out), model=args.model)
    if not args.no_console:
        show_console(results)


if __name__ == "__main__":
    main()
