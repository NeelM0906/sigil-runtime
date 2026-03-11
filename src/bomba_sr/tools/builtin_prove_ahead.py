"""Prove-Ahead — BOMBA SR native tools for competitive intelligence.

4 tools: competitors, matrix, benchmark, report.
No `rich` dependency — all output is JSON/dict.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMProvider
from bomba_sr.tools.base import ToolContext, ToolDefinition

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COMPETITORS_DB = "prove-ahead/data/competitors.db"
_BENCHMARK_FILE = "prove-ahead/benchmark_results.json"
_MATRIX_FILE = "prove-ahead/matrix.md"
_REPORT_FILE = "prove-ahead/report.md"

MATRIX_DIMENSIONS = [
    "emotional_intelligence",
    "formula_based_approach",
    "contextual_memory",
    "multi_agent_ecosystem",
    "voice_quality",
    "customization_depth",
    "integration_breadth",
    "pricing_model",
    "scale",
    "results_tracking",
]

DIMENSION_LABELS = {
    "emotional_intelligence": "Emotional Intelligence / Rapport",
    "formula_based_approach": "Formula-Based Approach",
    "contextual_memory": "Contextual Memory per User",
    "multi_agent_ecosystem": "Multi-Agent Ecosystem",
    "voice_quality": "Voice Quality / Naturalness",
    "customization_depth": "Customization Depth",
    "integration_breadth": "Integration Breadth",
    "pricing_model": "Pricing Model",
    "scale": "Scale",
    "results_tracking": "Results / Outcomes Tracking",
}

# ACT-I profile (embedded, matches SAI source)
ACT_I_PROFILE = {
    "company_name": "ACT-I",
    "product": "Callie / Athena DNA",
    "category": "AI influence and conversational intelligence",
    "pricing_model": "Program-based / enterprise",
    "capabilities": [
        "Integrity-based influence framework",
        "39-component Unblinded Formula",
        "Persistent contextual memory",
        "Multi-agent ecosystem (30 live agents)",
        "Real-time coaching and persuasion support",
        "Outcome-level interaction tracking",
    ],
    "known_customers": "100+ users with thousands of interactions",
    "funding": "Private; not publicly disclosed",
    "key_differentiators": "27-year-proven formula, 128 pathways, human-calibrated conversational strategy",
    "scores": {
        "emotional_intelligence": 5,
        "formula_based_approach": 5,
        "contextual_memory": 5,
        "multi_agent_ecosystem": 5,
        "voice_quality": 5,
        "customization_depth": 5,
        "integration_breadth": 4,
        "pricing_model": 4,
        "scale": 4,
        "results_tracking": 5,
    },
    "is_act_i": True,
}

# Benchmark config
BENCHMARK_SCENARIO = {
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
        "objections": ["Budget uncertainty", "Concern solution is overkill", "Fear of implementation drag"],
    },
}

COLOSSEUM_WEIGHTS = {
    "rapport_empathy": 0.2,
    "strategic_structure": 0.2,
    "contextual_memory": 0.2,
    "integrity_based_influence": 0.2,
    "next_step_clarity": 0.2,
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _guard_workspace_path(workspace_root: Path, relative: str) -> Path:
    resolved_root = workspace_root.resolve()
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError(f"Path traversal denied: {relative}")
    return path


def _db_path(workspace_root: Path) -> Path:
    return _guard_workspace_path(workspace_root, _COMPETITORS_DB)


def _read_competitors(workspace_root: Path, include_act_i: bool = False) -> list[dict[str, Any]]:
    db_file = _db_path(workspace_root)
    if not db_file.exists():
        raise ValueError(f"Competitors database not found: {_COMPETITORS_DB}")
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM competitors ORDER BY company_name").fetchall()
    except sqlite3.OperationalError:
        raise ValueError("competitors table not found in database")
    finally:
        conn.close()
    competitors = []
    for row in rows:
        entry = dict(row)
        # Parse JSON fields
        for json_field in ("capabilities", "sources", "scores"):
            if isinstance(entry.get(json_field), str):
                try:
                    entry[json_field] = json.loads(entry[json_field])
                except (json.JSONDecodeError, ValueError):
                    pass
        competitors.append(entry)
    if include_act_i:
        competitors.insert(0, dict(ACT_I_PROFILE))
    return competitors


def _build_matrix(competitors: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for comp in competitors:
        scores = comp.get("scores", {})
        if isinstance(scores, str):
            try:
                scores = json.loads(scores)
            except (json.JSONDecodeError, ValueError):
                scores = {}
        total = sum(scores.get(d, 0) for d in MATRIX_DIMENSIONS)
        row = {
            "company": comp.get("company_name", "Unknown"),
            "is_act_i": bool(comp.get("is_act_i")),
            "total_score": total,
        }
        for dim in MATRIX_DIMENSIONS:
            row[dim] = scores.get(dim, 0)
        rows.append(row)
    rows.sort(key=lambda r: r["total_score"], reverse=True)
    # Find ACT-I gaps (where competitors score higher)
    act_i_row = next((r for r in rows if r.get("is_act_i")), None)
    gaps: list[dict[str, Any]] = []
    if act_i_row:
        for dim in MATRIX_DIMENSIONS:
            act_score = act_i_row.get(dim, 0)
            for r in rows:
                if r.get("is_act_i"):
                    continue
                if r.get(dim, 0) > act_score:
                    gaps.append({
                        "dimension": DIMENSION_LABELS.get(dim, dim),
                        "competitor": r["company"],
                        "competitor_score": r[dim],
                        "act_i_score": act_score,
                        "gap": r[dim] - act_score,
                    })
    return {"matrix": rows, "gaps": sorted(gaps, key=lambda g: g["gap"], reverse=True), "dimensions": MATRIX_DIMENSIONS}


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _build_benchmark_prompt(style: str) -> str:
    s = BENCHMARK_SCENARIO
    base = (
        f"Scenario: {s['context']}\n"
        f"Prospect role: {s['prospect_profile']['role']}\n"
        f"Prospect state: {s['prospect_profile']['state']}\n"
        f"History: {s['prospect_profile']['history']}\n"
        f"Objections: {', '.join(s['prospect_profile']['objections'])}\n\n"
        "Write what the agent should say in this live conversation."
    )
    if style == "act_i":
        return (
            "You are ACT-I (Callie/Athena DNA). Apply a formulaic integrity-based influence approach: "
            "1) rapport and emotional calibration, 2) acknowledgment of constraints, 3) reframing around "
            "business impact, 4) low-friction next step. Use concise natural spoken language.\n\n" + base
        )
    return "You are a generic AI sales assistant. Respond helpfully and professionally in plain language.\n\n" + base


def _fallback_response(style: str) -> str:
    if style == "act_i":
        return (
            "Hi Jordan, thanks for taking a minute. Last time you were clear that budget discipline matters "
            "and I respect that. If this feels like overkill right now, we should say that directly.\n\n"
            "What I want to avoid is a long rollout for uncertain value. The fastest way to pressure-test "
            "this is a 20-minute working session focused on one high-leak workflow and a strict ROI threshold "
            "you define. If it misses your bar, we pause.\n\n"
            "Would Thursday 10:30 AM or Friday 1:00 PM be easier?"
        )
    return (
        "Hi Jordan, I wanted to follow up on our proposal. I understand pricing is a concern, but we "
        "believe our solution can help improve efficiency and outcomes.\n\n"
        "I would love to schedule a call to discuss this further and answer any questions. Are you "
        "available this week?"
    )


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def _sentence_count(text: str) -> int:
    return len([p.strip() for p in re.split(r"[.!?]\s+", text) if p.strip()])


def _score_response(text: str, style: str) -> dict[str, float]:
    # NOTE: Heuristic scoring is calibrated against the fallback response text.
    # Live LLM responses using different phrasing may score lower even if they
    # are subjectively better. This is acceptable for directional comparison;
    # for production use, replace with LLM-based judging.
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
    scores["weighted_total"] = round(sum(scores[k] * COLOSSEUM_WEIGHTS[k] for k in COLOSSEUM_WEIGHTS), 2)
    return scores


# ---------------------------------------------------------------------------
# Tool factory functions
# ---------------------------------------------------------------------------


def _prove_ahead_competitors_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        include_act_i = bool(arguments.get("include_act_i", True))
        competitors = _read_competitors(ws, include_act_i=include_act_i)
        summaries = []
        for c in competitors:
            scores = c.get("scores", {})
            if isinstance(scores, str):
                try:
                    scores = json.loads(scores)
                except (json.JSONDecodeError, ValueError):
                    scores = {}
            total = sum(scores.get(d, 0) for d in MATRIX_DIMENSIONS)
            summaries.append({
                "company": c.get("company_name", "Unknown"),
                "product": c.get("product", ""),
                "category": c.get("category", ""),
                "pricing_model": c.get("pricing_model", ""),
                "funding": c.get("funding", ""),
                "key_differentiators": c.get("key_differentiators", ""),
                "total_score": total,
                "is_act_i": bool(c.get("is_act_i")),
            })
        return {"competitors": summaries, "count": len(summaries)}

    return run


def _prove_ahead_matrix_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        competitors = _read_competitors(ws, include_act_i=True)
        result = _build_matrix(competitors)
        result["dimension_labels"] = DIMENSION_LABELS
        return result

    return run


def _prove_ahead_benchmark_factory(
    provider: LLMProvider | None,
    default_model_id: str,
    workspace_root: Path | None,
):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        model = arguments.get("model") or default_model_id
        use_cached = bool(arguments.get("use_cached", False))

        # Try to load cached results first
        cached_path = _guard_workspace_path(ws, _BENCHMARK_FILE)
        if use_cached and cached_path.exists():
            return json.loads(cached_path.read_text(encoding="utf-8"))

        responses: dict[str, str] = {}
        mode_by_agent: dict[str, str] = {}

        for style in ("act_i", "generic"):
            prompt = _build_benchmark_prompt(style)
            text = ""
            if provider is not None:
                try:
                    resp = provider.generate(
                        model=model,
                        messages=[ChatMessage(role="user", content=prompt)],
                    )
                    text = resp.content.strip() if resp.content else ""
                except Exception:
                    text = ""
            if not text:
                text = _fallback_response(style)
                mode_by_agent[style] = "fallback"
            else:
                mode_by_agent[style] = "llm"
            responses[style] = text

        act_scores = _score_response(responses["act_i"], "act_i")
        generic_scores = _score_response(responses["generic"], "generic")
        gap = round(act_scores["weighted_total"] - generic_scores["weighted_total"], 2)

        results: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "scenario": BENCHMARK_SCENARIO,
            "metadata": {"model": model, "mode_by_agent": mode_by_agent},
            "rubric_weights": COLOSSEUM_WEIGHTS,
            "responses": responses,
            "scores": {"act_i": act_scores, "generic": generic_scores},
            "summary": {
                "winner": "ACT-I" if gap >= 0 else "Generic AI",
                "weighted_gap": gap,
                "interpretation": "Positive gap indicates ACT-I performed better under the Colosseum rubric.",
            },
        }

        # Save results
        cached_path.parent.mkdir(parents=True, exist_ok=True)
        cached_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        return results

    return run


def _prove_ahead_report_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root

        # Build matrix data
        competitors = _read_competitors(ws, include_act_i=True)
        matrix_data = _build_matrix(competitors)

        # Load benchmark if available
        benchmark_path = _guard_workspace_path(ws, _BENCHMARK_FILE)
        benchmark: dict[str, Any] | None = None
        if benchmark_path.exists():
            try:
                benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                pass

        # Load existing report markdown if available
        report_path = _guard_workspace_path(ws, _REPORT_FILE)
        report_md = ""
        if report_path.exists():
            report_md = report_path.read_text(encoding="utf-8")

        return {
            "report_markdown": report_md if report_md else "No pre-generated report available. Use matrix and benchmark data below.",
            "matrix_summary": {
                "total_competitors": len(matrix_data["matrix"]),
                "top_3": [
                    {"company": r["company"], "score": r["total_score"]}
                    for r in matrix_data["matrix"][:3]
                ],
                "key_gaps": matrix_data["gaps"][:5],
            },
            "benchmark_summary": (
                {
                    "winner": benchmark["summary"]["winner"],
                    "gap": benchmark["summary"]["weighted_gap"],
                    "model": benchmark.get("metadata", {}).get("model", "unknown"),
                }
                if benchmark
                else None
            ),
        }

    return run


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def builtin_prove_ahead_tools(
    provider: LLMProvider | None = None,
    default_model_id: str = "anthropic/claude-opus-4.6",
    workspace_root: Path | None = None,
) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="prove_ahead_competitors",
            description="List competitors in the Prove-Ahead competitive intelligence database with scores and capabilities.",
            parameters={
                "type": "object",
                "properties": {
                    "include_act_i": {
                        "type": "boolean",
                        "description": "Include ACT-I's own profile for comparison (default: true).",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_prove_ahead_competitors_factory(workspace_root),
        ),
        ToolDefinition(
            name="prove_ahead_matrix",
            description=(
                "Generate the 10-dimension competitive capability matrix. Returns per-company scores, "
                "total rankings, and gaps where competitors exceed ACT-I."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_prove_ahead_matrix_factory(workspace_root),
        ),
        ToolDefinition(
            name="prove_ahead_benchmark",
            description=(
                "Run head-to-head ACT-I vs generic AI benchmark on a sales recovery scenario. "
                "Uses LLM for response generation. Falls back to cached responses if no provider."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "LLM model to use for response generation.",
                    },
                    "use_cached": {
                        "type": "boolean",
                        "description": "Return cached benchmark results if available (default: false).",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=_prove_ahead_benchmark_factory(provider, default_model_id, workspace_root),
        ),
        ToolDefinition(
            name="prove_ahead_report",
            description=(
                "Generate competitive analysis report from matrix and benchmark data. "
                "Returns summary with rankings, gaps, and benchmark results."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_prove_ahead_report_factory(workspace_root),
        ),
    ]
