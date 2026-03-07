"""Health snapshot for agentic loop status reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HealthSnapshot:
    iteration: int
    max_iterations: int
    budget_used_usd: float
    budget_limit_usd: float
    budget_remaining_pct: float
    total_tool_calls: int
    failed_tool_calls: int
    denied_tool_calls: int
    approval_blocked_calls: int
    loop_detected: bool
    current_model: str

    def as_system_text(self) -> str:
        lines = [
            "<health_status>",
            f"  iteration: {self.iteration}/{self.max_iterations}",
            f"  budget: ${self.budget_used_usd:.4f} / ${self.budget_limit_usd:.2f} ({self.budget_remaining_pct:.0f}% remaining)",
            f"  tool_calls: {self.total_tool_calls} total, {self.failed_tool_calls} failed, {self.denied_tool_calls} denied, {self.approval_blocked_calls} blocked",
            f"  loop_anomaly: {self.loop_detected}",
            f"  model: {self.current_model}",
            "</health_status>",
        ]
        return "\n".join(lines)


def build_health_snapshot(state: Any, config: Any, model_id: str) -> HealthSnapshot:
    total = len(state.tool_calls_history)
    failed = sum(1 for tc in state.tool_calls_history if tc.status == "error")
    denied = sum(1 for tc in state.tool_calls_history if tc.status == "denied")
    blocked = sum(1 for tc in state.tool_calls_history if tc.status == "approval_required")
    budget_used = float(getattr(state, "estimated_cost_usd", 0.0))
    budget_limit = float(getattr(config, "budget_limit_usd", 2.0))
    remaining_pct = max(0.0, (1 - budget_used / budget_limit) * 100.0) if budget_limit > 0 else 100.0
    return HealthSnapshot(
        iteration=int(getattr(state, "iteration", 0)),
        max_iterations=int(getattr(config, "max_iterations", 1)),
        budget_used_usd=budget_used,
        budget_limit_usd=budget_limit,
        budget_remaining_pct=remaining_pct,
        total_tool_calls=total,
        failed_tool_calls=failed,
        denied_tool_calls=denied,
        approval_blocked_calls=blocked,
        loop_detected=False,
        current_model=str(getattr(state, "current_model_id", model_id)),
    )
