from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMProvider
from bomba_sr.storage.db import RuntimeDB, dict_from_row


@dataclass
class SelfEvaluator:
    provider: LLMProvider
    db: RuntimeDB

    def evaluate(self, tenant_id: str, session_id: str, model_id: str) -> dict[str, Any]:
        recent_loops = self._get_recent_loops(tenant_id=tenant_id, session_id=session_id, limit=10)
        prompt = self._build_evaluation_prompt(recent_loops)
        response = self.provider.generate(
            model=model_id,
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "Evaluate your last runtime turns. Return strict JSON with keys "
                        "tool_efficiency, memory_quality, goal_completion, recommendations, policy_updates."
                    ),
                ),
                ChatMessage(role="user", content=prompt),
            ],
        )
        parsed = self._parse_evaluation(response.text)
        parsed["evaluated_loops"] = len(recent_loops)
        parsed["model"] = response.model or model_id
        return parsed

    def _get_recent_loops(self, tenant_id: str, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT *
            FROM loop_executions
            WHERE tenant_id = ? AND session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tenant_id, session_id, max(1, int(limit))),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict_from_row(row)
            raw_calls = item.get("tool_calls_json")
            try:
                item["tool_calls"] = json.loads(raw_calls) if isinstance(raw_calls, str) and raw_calls else []
            except json.JSONDecodeError:
                item["tool_calls"] = []
            out.append(item)
        return out

    def _build_evaluation_prompt(self, recent_loops: list[dict[str, Any]]) -> str:
        compact = []
        for loop in recent_loops:
            compact.append(
                {
                    "turn_id": loop.get("turn_id"),
                    "iterations": int(loop.get("iterations") or 0),
                    "stopped_reason": loop.get("stopped_reason"),
                    "input_tokens": int(loop.get("total_input_tokens") or 0),
                    "output_tokens": int(loop.get("total_output_tokens") or 0),
                    "tool_calls": loop.get("tool_calls", []),
                }
            )
        return (
            "Based on these recent loop executions, score yourself from 0.0 to 1.0 and suggest policy updates.\n"
            "Output JSON only.\n\n"
            + json.dumps(compact, ensure_ascii=True)
        )

    @staticmethod
    def _parse_evaluation(text: str) -> dict[str, Any]:
        payload = SelfEvaluator._extract_json_payload(text)
        if payload is None:
            return {
                "tool_efficiency": 0.5,
                "memory_quality": 0.5,
                "goal_completion": 0.5,
                "recommendations": [],
                "policy_updates": {},
                "raw": text,
            }

        recommendations = payload.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []
        recommendations_out = [str(item) for item in recommendations if isinstance(item, (str, int, float))]

        policy_updates = payload.get("policy_updates")
        if not isinstance(policy_updates, dict):
            policy_updates = {}

        return {
            "tool_efficiency": SelfEvaluator._bounded_float(payload.get("tool_efficiency"), default=0.5),
            "memory_quality": SelfEvaluator._bounded_float(payload.get("memory_quality"), default=0.5),
            "goal_completion": SelfEvaluator._bounded_float(payload.get("goal_completion"), default=0.5),
            "recommendations": recommendations_out,
            "policy_updates": policy_updates,
            "raw": text,
        }

    @staticmethod
    def _extract_json_payload(text: str) -> dict[str, Any] | None:
        stripped = text.strip()
        if not stripped:
            return None
        candidates: list[str] = [stripped]
        fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
        candidates.extend(fenced)
        brace = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if brace:
            candidates.append(brace.group(0))

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _bounded_float(value: Any, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        if parsed < 0.0:
            return 0.0
        if parsed > 1.0:
            return 1.0
        return parsed
