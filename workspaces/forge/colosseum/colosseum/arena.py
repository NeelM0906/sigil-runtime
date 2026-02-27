"""
The Arena — Where beings face scenarios and compete.
"""

import os
import json
import asyncio
import sqlite3
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI, AsyncOpenAI

from .scenarios import Scenario, scenario_to_prompt, scenario_to_dict
from .beings import Being, save_being, DB_PATH
from .judge import judge_response, Judgment, judgment_to_dict

sync_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
async_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@dataclass
class RoundResult:
    scenario: Scenario
    being: Being
    response: str
    judgment: Judgment
    model_used: str


def generate_response(
    being: Being,
    scenario: Scenario,
    model: str = "gpt-4o-mini"
) -> str:
    """Have a being respond to a scenario (sync)."""
    prompt = scenario_to_prompt(scenario)

    result = sync_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": being.system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1000,
    )

    return result.choices[0].message.content


async def async_generate_response(
    being: Being,
    scenario: Scenario,
    model: str = "gpt-4o-mini"
) -> str:
    """Have a being respond to a scenario (async)."""
    prompt = scenario_to_prompt(scenario)

    result = await async_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": being.system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1000,
    )

    return result.choices[0].message.content


def run_round(
    beings: list[Being],
    scenario: Scenario,
    model: str = "gpt-4o-mini",
    judge_model: str = "gpt-4o-mini",
) -> list[RoundResult]:
    """Run one round: all beings respond to the same scenario, all get judged."""
    results = []

    for being in beings:
        # Generate response
        response = generate_response(being, scenario, model=model)

        # Judge it
        scenario_prompt = scenario_to_prompt(scenario)
        judgment = judge_response(scenario_prompt, being.name, response, model=judge_model)

        results.append(RoundResult(
            scenario=scenario,
            being=being,
            response=response,
            judgment=judgment,
            model_used=model,
        ))

    # Determine winner(s)
    if results:
        best_score = max(r.judgment.scores.overall_mastery for r in results)
        for r in results:
            won = r.judgment.scores.overall_mastery == best_score
            r.being.record_result(r.judgment.scores.overall_mastery, won)
            save_being(r.being)

    # Save round results to DB
    _save_round_results(results)

    return results


async def async_run_round(
    beings: list[Being],
    scenario: Scenario,
    model: str = "gpt-4o-mini",
    judge_model: str = "gpt-4o-mini",
    tournament_id: Optional[str] = None,
) -> list[RoundResult]:
    """Run one round asynchronously — all beings respond in parallel."""

    # Generate all responses in parallel
    response_tasks = [
        async_generate_response(being, scenario, model=model)
        for being in beings
    ]
    responses = await asyncio.gather(*response_tasks, return_exceptions=True)

    results = []
    scenario_prompt = scenario_to_prompt(scenario)

    for being, response in zip(beings, responses):
        if isinstance(response, Exception):
            response = f"[ERROR: {str(response)}]"

        # Judge (these could also be parallelized but let's be gentle on the API)
        judgment = judge_response(scenario_prompt, being.name, response, model=judge_model)

        results.append(RoundResult(
            scenario=scenario,
            being=being,
            response=response,
            judgment=judgment,
            model_used=model,
        ))

    # Determine winner(s)
    if results:
        best_score = max(r.judgment.scores.overall_mastery for r in results)
        for r in results:
            won = r.judgment.scores.overall_mastery == best_score
            r.being.record_result(r.judgment.scores.overall_mastery, won)
            save_being(r.being)

    _save_round_results(results, tournament_id)

    return results


def _save_round_results(results: list[RoundResult], tournament_id: Optional[str] = None):
    """Save round results to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for r in results:
        best_score = max(res.judgment.scores.overall_mastery for res in results) if results else 0
        won = r.judgment.scores.overall_mastery == best_score
        c.execute("""
            INSERT INTO rounds (scenario_id, scenario_json, being_id, response, scores_json,
                                mastery_score, won, tournament_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.scenario.id,
            json.dumps(scenario_to_dict(r.scenario)),
            r.being.id,
            r.response,
            json.dumps(judgment_to_dict(r.judgment)),
            r.judgment.scores.overall_mastery,
            won,
            tournament_id,
        ))
    conn.commit()
    conn.close()


def get_recent_rounds(limit: int = 50) -> list[dict]:
    """Get recent round results."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT r.*, b.name as being_name
        FROM rounds r
        LEFT JOIN beings b ON r.being_id = b.id
        ORDER BY r.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
