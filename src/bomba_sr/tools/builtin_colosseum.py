"""Colosseum v2 — BOMBA SR native tools for the CHDDIA² tournament engine.

5 tools: run_round, leaderboard, being_list, evolve, scenario_list.
All LLM calls route through BOMBA's LLMProvider (synchronous).
"""
from __future__ import annotations

import copy
import json
import random
import time
from pathlib import Path
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMProvider
from bomba_sr.tools.base import ToolContext, ToolDefinition

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

_LEADERBOARD_FILE = "colosseum/v2/data/results/leaderboard_latest.json"
_BEINGS_FILE = "colosseum/v2/data/beings.json"
_JUDGES_FILE = "colosseum/v2/data/judges.json"
_SCENARIOS_FILE = "colosseum/v2/data/scenarios.json"
_RESULTS_DIR = "colosseum/v2/data/results"


def _guard_workspace_path(workspace_root: Path, relative: str) -> Path:
    resolved_root = workspace_root.resolve()
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError(f"Path traversal denied: {relative}")
    return path


def _load_json(workspace_root: Path, relative: str) -> Any:
    path = _guard_workspace_path(workspace_root, relative)
    if not path.exists():
        raise ValueError(f"Colosseum data file not found: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(workspace_root: Path, relative: str, data: Any) -> Path:
    path = _guard_workspace_path(workspace_root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# LLM call helpers (synchronous, using BOMBA provider)
# ---------------------------------------------------------------------------


def _generate_being_response(
    provider: LLMProvider,
    model: str,
    being: dict[str, Any],
    scenario: dict[str, Any],
) -> str:
    prompt = (
        f"SCENARIO: {scenario['title']}\n"
        f"COMPANY: {scenario['company']}\n"
        f"SITUATION: {scenario['situation']}\n"
        f"PERSON: {json.dumps(scenario['person'])}\n"
        f"SUCCESS CRITERIA: {scenario['success_criteria']}\n\n"
        "Respond as your character would in this exact situation. "
        "Be specific, be masterful, be real. This is not a test — this is the moment. Execute."
    )
    resp = provider.generate(
        model=model,
        messages=[
            ChatMessage(role="system", content=being.get("dna", "")),
            ChatMessage(role="user", content=prompt),
        ],
    )
    return resp.content.strip() if resp.content else "[no response]"


def _judge_being_response(
    provider: LLMProvider,
    model: str,
    judge_key: str,
    judge_data: dict[str, Any],
    being: dict[str, Any],
    scenario: dict[str, Any],
    response_text: str,
) -> dict[str, Any]:
    prompt = (
        f"BEING: {being['title']} ({being.get('area', '')})\n"
        f"SCENARIO: {scenario['title']} — {scenario['situation']}\n"
        f"SUCCESS CRITERIA: {scenario['success_criteria']}\n\n"
        f"THE BEING'S RESPONSE:\n{response_text}\n\n"
        "Score this response according to your criteria. Be rigorous. Be specific. "
        "Return ONLY valid JSON."
    )
    resp = provider.generate(
        model=model,
        messages=[
            ChatMessage(role="system", content=judge_data.get("prompt", "")),
            ChatMessage(role="user", content=prompt),
        ],
    )
    content = resp.content.strip() if resp.content else ""
    # Extract JSON from possible markdown fences
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, ValueError):
        return {"error": "parse_error", "overall": 5.0, "feedback": "Judge response was not valid JSON"}


# ---------------------------------------------------------------------------
# Tool factory functions
# ---------------------------------------------------------------------------


def _colosseum_run_round_factory(
    provider: LLMProvider,
    default_model_id: str,
    workspace_root: Path | None,
):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        beings = _load_json(ws, _BEINGS_FILE)
        judges = _load_json(ws, _JUDGES_FILE)
        scenarios = _load_json(ws, _SCENARIOS_FILE)
        if not isinstance(beings, list):
            raise ValueError("beings.json must be a JSON array")
        if not isinstance(judges, dict):
            raise ValueError("judges.json must be a JSON object")
        if not isinstance(scenarios, dict):
            raise ValueError("scenarios.json must be a JSON object")
        model = arguments.get("model") or default_model_id

        # Optional filters
        area_filter = arguments.get("area_filter")
        being_ids = arguments.get("being_ids")
        max_beings = int(arguments.get("max_beings") or len(beings))

        filtered = beings
        if area_filter:
            filtered = [b for b in filtered if b.get("area_key") == area_filter or b.get("area") == area_filter]
        if being_ids:
            id_set = set(being_ids) if isinstance(being_ids, list) else {being_ids}
            filtered = [b for b in filtered if b.get("id") in id_set]
        filtered = filtered[:max_beings]

        if not filtered:
            return {"error": "no beings matched filters", "beings_total": len(beings)}

        all_results: list[dict[str, Any]] = []
        for being in filtered:
            scenario = scenarios.get(being["id"])
            if not scenario:
                continue
            response_text = _generate_being_response(provider, model, being, scenario)
            scores: dict[str, Any] = {}
            overall_scores: list[float] = []
            for jkey, jdata in judges.items():
                score = _judge_being_response(provider, model, jkey, jdata, being, scenario, response_text)
                scores[jkey] = score
                if isinstance(score, dict) and "overall" in score:
                    try:
                        overall_scores.append(float(score["overall"]))
                    except (ValueError, TypeError):
                        pass

            result = {
                "being_id": being["id"],
                "being_title": being["title"],
                "area": being.get("area", ""),
                "scenario": scenario["title"],
                "response_preview": response_text[:300],
                "scores": scores,
                "average_overall": round(sum(overall_scores) / len(overall_scores), 4) if overall_scores else 0.0,
                "timestamp": time.time(),
            }
            all_results.append(result)

        # Save round results
        results_file = f"{_RESULTS_DIR}/round_{int(time.time())}.json"
        _save_json(ws, results_file, all_results)

        # Update leaderboard — persist full scores list so history survives across rounds
        try:
            existing_lb = _load_json(ws, _LEADERBOARD_FILE)
        except ValueError:
            existing_lb = []
        lb_map: dict[str, dict[str, Any]] = {}
        for e in existing_lb:
            if not isinstance(e, dict):
                continue
            lb_map[e["id"]] = {
                "id": e["id"],
                "title": e.get("title", ""),
                "area": e.get("area", ""),
                "scores": list(e.get("scores", [])),
            }
        for r in all_results:
            bid = r["being_id"]
            if bid not in lb_map:
                lb_map[bid] = {"id": bid, "title": r["being_title"], "area": r["area"], "scores": []}
            lb_map[bid]["scores"].append(r["average_overall"])
        new_lb = []
        for bid, data in lb_map.items():
            scores_list = data["scores"]
            avg = sum(scores_list) / len(scores_list) if scores_list else 0.0
            new_lb.append({
                "id": bid,
                "title": data["title"],
                "area": data.get("area", ""),
                "average": round(avg, 4),
                "scores": scores_list,
            })
        new_lb.sort(key=lambda x: x["average"], reverse=True)
        _save_json(ws, _LEADERBOARD_FILE, new_lb)

        sorted_results = sorted(all_results, key=lambda x: x["average_overall"], reverse=True)
        return {
            "round_results": len(all_results),
            "model_used": model,
            "top_5": [
                {"title": r["being_title"], "area": r["area"], "score": r["average_overall"]}
                for r in sorted_results[:5]
            ],
            "bottom_3": [
                {"title": r["being_title"], "area": r["area"], "score": r["average_overall"]}
                for r in sorted_results[-3:]
            ],
            "results_file": results_file,
        }

    return run


def _colosseum_leaderboard_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        try:
            leaderboard = _load_json(ws, _LEADERBOARD_FILE)
        except ValueError:
            return {"leaderboard": [], "message": "No tournament results yet."}
        top_n = int(arguments.get("top_n") or 0)
        if top_n > 0:
            leaderboard = leaderboard[:top_n]
        return {"leaderboard": leaderboard, "total_beings": len(leaderboard)}

    return run


def _colosseum_being_list_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        beings = _load_json(ws, _BEINGS_FILE)
        area_filter = arguments.get("area_filter")
        if area_filter:
            beings = [b for b in beings if b.get("area_key") == area_filter or b.get("area") == area_filter]
        summary = [
            {
                "id": b["id"],
                "title": b["title"],
                "area": b.get("area", ""),
                "type": b.get("type", ""),
                "focus": b.get("focus", "")[:200],
                "generation": b.get("generation", 0),
            }
            for b in beings
        ]
        return {"beings": summary, "count": len(summary)}

    return run


def _colosseum_evolve_factory(
    provider: LLMProvider,
    default_model_id: str,
    workspace_root: Path | None,
):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        beings = _load_json(ws, _BEINGS_FILE)
        model = arguments.get("model") or default_model_id

        try:
            leaderboard = _load_json(ws, _LEADERBOARD_FILE)
        except ValueError:
            return {"error": "No leaderboard data. Run a tournament round first."}

        lb_scores = {e["id"]: e.get("average", 0) for e in leaderboard if isinstance(e, dict)}
        scored_beings = sorted(beings, key=lambda b: lb_scores.get(b["id"], 0), reverse=True)

        n = len(scored_beings)
        top_30 = scored_beings[:max(1, int(n * 0.3))]
        mid_40 = scored_beings[int(n * 0.3):int(n * 0.7)]
        bottom_30 = scored_beings[int(n * 0.7):]

        evolved: list[dict[str, Any]] = []

        # Top 30% survive unchanged but increment generation
        for b in top_30:
            new_b = copy.deepcopy(b)
            new_b["generation"] = b.get("generation", 0) + 1
            evolved.append(new_b)

        # Middle 40% mutate DNA via LLM
        for b in mid_40:
            mutation_prompt = (
                f"This being scored in the middle tier. Its current DNA focus is: {b.get('focus', '')}\n"
                f"Area: {b.get('area', '')}, Title: {b['title']}\n"
                f"Score: {lb_scores.get(b['id'], 'unknown')}\n\n"
                "Suggest a refined, more specific DNA focus (1-2 sentences) that would help this being "
                "perform better in its area. Be concrete and actionable."
            )
            resp = provider.generate(
                model=model,
                messages=[ChatMessage(role="user", content=mutation_prompt)],
            )
            new_focus = resp.content.strip() if resp.content else b.get("focus", "")
            new_b = copy.deepcopy(b)
            new_b["focus"] = new_focus[:500]
            new_b["generation"] = b.get("generation", 0) + 1
            new_b["mutation"] = "llm_refine"
            evolved.append(new_b)

        # Bottom 30% crossover: combine DNA from two random top performers
        for b in bottom_30:
            parent1 = random.choice(top_30)
            parent2 = random.choice(top_30) if len(top_30) > 1 else parent1
            crossover_prompt = (
                f"Create a new DNA focus for this being by combining strengths of two top performers.\n"
                f"Being: {b['title']} (Area: {b.get('area', '')})\n"
                f"Parent 1: {parent1['title']} — Focus: {parent1.get('focus', '')}\n"
                f"Parent 2: {parent2['title']} — Focus: {parent2.get('focus', '')}\n\n"
                "Write a new focus (1-2 sentences) that combines the best of both parents "
                "while staying true to this being's area."
            )
            resp = provider.generate(
                model=model,
                messages=[ChatMessage(role="user", content=crossover_prompt)],
            )
            new_focus = resp.content.strip() if resp.content else b.get("focus", "")
            new_b = copy.deepcopy(b)
            new_b["focus"] = new_focus[:500]
            new_b["generation"] = b.get("generation", 0) + 1
            new_b["mutation"] = "crossover"
            new_b["parents"] = [parent1["id"], parent2["id"]]
            evolved.append(new_b)

        # Save evolved generation
        gen_num = max((b.get("generation", 0) for b in evolved), default=1)
        _save_json(ws, _BEINGS_FILE, evolved)
        _save_json(ws, f"{_RESULTS_DIR}/beings_gen{gen_num}.json", evolved)

        return {
            "generation": gen_num,
            "survivors": len(top_30),
            "mutated": len(mid_40),
            "crossover": len(bottom_30),
            "total": len(evolved),
        }

    return run


def _colosseum_scenario_list_factory(workspace_root: Path | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        ws = workspace_root or context.workspace_root
        scenarios = _load_json(ws, _SCENARIOS_FILE)
        if not isinstance(scenarios, dict):
            raise ValueError("scenarios.json must be a JSON object")
        area_filter = arguments.get("area_filter")
        summaries: list[dict[str, Any]] = []
        for sid, s in scenarios.items():
            if area_filter and not sid.startswith(area_filter):
                continue
            summaries.append({
                "id": sid,
                "title": s.get("title", ""),
                "company": s.get("company", ""),
                "person": s.get("person", {}).get("name", ""),
                "success_criteria": s.get("success_criteria", "")[:200],
            })
        return {"scenarios": summaries, "count": len(summaries)}

    return run


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def builtin_colosseum_tools(
    provider: LLMProvider,
    default_model_id: str = "gpt-4o-mini",
    workspace_root: Path | None = None,
) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="colosseum_run_round",
            description=(
                "Run a Colosseum tournament round: selected beings generate responses to their scenarios "
                "and are scored by all 5 judges. Returns top/bottom performers and saves results."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "area_filter": {
                        "type": "string",
                        "description": "Optional area key to filter beings (e.g. 'sales_influence').",
                    },
                    "being_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific being IDs to include.",
                    },
                    "max_beings": {
                        "type": "integer",
                        "description": "Maximum number of beings to process (default: all).",
                    },
                    "model": {
                        "type": "string",
                        "description": "LLM model to use (default: configured colosseum model).",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_colosseum_run_round_factory(provider, default_model_id, workspace_root),
        ),
        ToolDefinition(
            name="colosseum_leaderboard",
            description="Read the current Colosseum leaderboard showing all beings ranked by average score.",
            parameters={
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Return only the top N entries (0 = all).",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_colosseum_leaderboard_factory(workspace_root),
        ),
        ToolDefinition(
            name="colosseum_being_list",
            description="List all Colosseum beings with their DNA summary, generation, and area.",
            parameters={
                "type": "object",
                "properties": {
                    "area_filter": {
                        "type": "string",
                        "description": "Optional area key to filter (e.g. 'vision_leadership').",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_colosseum_being_list_factory(workspace_root),
        ),
        ToolDefinition(
            name="colosseum_evolve",
            description=(
                "Run genetic evolution on beings: top 30% survive, middle 40% get LLM-refined DNA, "
                "bottom 30% get crossover DNA from top performers. Saves new generation."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "LLM model for evolution prompts (default: configured colosseum model).",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_colosseum_evolve_factory(provider, default_model_id, workspace_root),
        ),
        ToolDefinition(
            name="colosseum_scenario_list",
            description="List all Colosseum scenarios with title, company, person, and success criteria.",
            parameters={
                "type": "object",
                "properties": {
                    "area_filter": {
                        "type": "string",
                        "description": "Optional area key prefix to filter scenarios.",
                    },
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_colosseum_scenario_list_factory(workspace_root),
        ),
    ]
