from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

from bomba_sr.governance.policy_pipeline import ResolvedPolicy
from bomba_sr.llm.providers import ChatMessage, LLMProvider, LLMResponse
from bomba_sr.runtime.health import build_health_snapshot
from bomba_sr.tools.base import ToolCallResult, ToolContext, ToolExecutor


# Approximate cost per 1M tokens (USD). Keyed by model ID prefix.
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "claude-opus": (5.0, 25.0),
    "claude-sonnet": (3.0, 15.0),
    "claude-haiku": (1.0, 5.0),
    "gpt5.3": (3.0, 10.0),
}

READ_ONLY_ACTIONS = frozenset({"read"})


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    normalized = (model_id or "").lower()
    for prefix, (input_cost, output_cost) in MODEL_COSTS.items():
        if prefix in normalized:
            return (input_tokens / 1_000_000 * input_cost) + (output_tokens / 1_000_000 * output_cost)
    return (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)


@dataclass(frozen=True)
class LoopConfig:
    max_iterations: int = 25
    max_tool_calls_per_iteration: int = 10
    token_budget_fraction: float = 0.7
    loop_detection_window: int = 5
    stop_on_approval_required: bool = True
    budget_limit_usd: float = 2.0
    budget_hard_stop_pct: float = 0.9
    parallel_read_tools: bool = True
    max_parallel_workers: int = 4


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LoopState:
    iteration: int = 0
    messages: list[ChatMessage] = field(default_factory=list)
    tool_calls_history: list[ToolCallResult] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    stopped_reason: str | None = None
    final_text: str = ""
    current_model_id: str = ""
    active_tool_overrides: set[str] = field(default_factory=set)
    denied_tools: set[str] = field(default_factory=set)
    health_message_idx: int | None = None
    tool_schemas_dirty: bool = False


@dataclass(frozen=True)
class LoopResult:
    final_text: str
    iterations: int
    tool_calls: list[ToolCallResult]
    stopped_reason: str | None
    total_input_tokens: int
    total_output_tokens: int
    messages: list[dict[str, Any]]
    estimated_cost_usd: float
    budget_exhausted: bool


class AgenticLoop:
    def __init__(
        self,
        provider: LLMProvider,
        tool_executor: ToolExecutor,
        config: LoopConfig,
    ) -> None:
        self.provider = provider
        self.tool_executor = tool_executor
        self.config = config

    def run(
        self,
        initial_messages: list[ChatMessage],
        tool_schemas: list[dict[str, Any]],
        context: ToolContext,
        resolved_policy: ResolvedPolicy,
        model_id: str,
        tool_format: str = "openai",
        on_iteration: Any = None,
    ) -> LoopResult:
        state = LoopState(
            messages=list(initial_messages),
            current_model_id=model_id,
            denied_tools=set(resolved_policy.denied_tools),
        )

        while state.iteration < self.config.max_iterations:
            state.iteration += 1
            self._inject_health_as_message(state, model_id)

            effective_schemas = self._effective_tool_schemas(
                base_tool_schemas=tool_schemas,
                resolved_policy=resolved_policy,
                state=state,
                tool_format=tool_format,
            )

            # ── Log Point C: LLM API call ──
            _is_orch = any("subtask:" in m.content or "orchestration:" in (m.content if isinstance(m.content, str) else "") for m in state.messages[:3] if isinstance(m.content, str))
            if _is_orch:
                log.warning(f"[ORCH] ── Log Point C: Sending to LLM ──")
                log.warning(f"[ORCH] Model: {state.current_model_id} via {self.provider.provider_name}")
                log.warning(f"[ORCH] Message count: {len(state.messages)}")
                _sys_len = sum(len(m.content) if isinstance(m.content, str) else 0 for m in state.messages if m.role == "system")
                log.warning(f"[ORCH] System prompt length: {_sys_len} chars")
                log.warning(f"[ORCH] Tool schemas count: {len(effective_schemas)}")
                log.warning(f"[ORCH] Iteration: {state.iteration}")

            try:
                response = self.provider.generate(
                    model=state.current_model_id,
                    messages=state.messages,
                    tools=effective_schemas or None,
                )
            except Exception as exc:
                if _is_orch:
                    log.warning(f"[ORCH] ── Log Point D: LLM ERROR ──")
                    log.warning(f"[ORCH] Exception: {exc}")
                state.stopped_reason = "error"
                state.final_text = f"loop_error: {exc}"
                break

            # ── Log Point D: LLM response received ──
            if _is_orch:
                log.warning(f"[ORCH] ── Log Point D: Response received ──")
                log.warning(f"[ORCH] Response length: {len(response.text)} chars")
                log.warning(f"[ORCH] Response model: {response.model}")
                log.warning(f"[ORCH] Stop reason: {response.stop_reason}")
                log.warning(f"[ORCH] Response preview: {response.text[:300]}")
                if not response.text:
                    log.warning(f"[ORCH] EMPTY RESPONSE — raw keys: {list(response.raw.keys())}")
                    log.warning(f"[ORCH] Raw choices: {response.raw.get('choices', response.raw.get('content', 'N/A'))}")

            delta_input, delta_output = self._accumulate_usage(response, state)
            state.estimated_cost_usd += estimate_cost(
                response.model or state.current_model_id,
                delta_input,
                delta_output,
            )

            if state.estimated_cost_usd >= self.config.budget_limit_usd * self.config.budget_hard_stop_pct:
                state.stopped_reason = "budget_exhausted"
                state.final_text = response.text or ""
                break

            tool_calls = self._parse_tool_calls(response)
            if not tool_calls:
                state.final_text = response.text
                break

            # Preserve any text the LLM returned alongside tool calls so
            # that if the loop exits (max_iterations / loop_detected) we
            # still have the last meaningful response.
            if response.text:
                state.final_text = response.text

            if len(tool_calls) > self.config.max_tool_calls_per_iteration:
                tool_calls = tool_calls[: self.config.max_tool_calls_per_iteration]

            context.loop_state_ref = state
            results = self._execute_tool_calls(
                tool_calls=tool_calls,
                context=context,
                resolved_policy=resolved_policy,
            )
            state.tool_calls_history.extend(results)

            if on_iteration is not None:
                try:
                    on_iteration(state.iteration, state)
                except Exception:
                    pass

            state.messages.extend(self._assistant_and_tool_messages(response, tool_calls, results))

            if self.config.stop_on_approval_required and any(r.status == "approval_required" for r in results):
                state.stopped_reason = "approval_required"
                break
            if self._detect_loop(state):
                state.stopped_reason = "loop_detected"
                break
        else:
            state.stopped_reason = "max_iterations"

        serialized = []
        for msg in state.messages:
            serialized.append({"role": msg.role, "content": msg.content})
        return LoopResult(
            final_text=state.final_text,
            iterations=state.iteration,
            tool_calls=list(state.tool_calls_history),
            stopped_reason=state.stopped_reason,
            total_input_tokens=state.total_input_tokens,
            total_output_tokens=state.total_output_tokens,
            messages=serialized,
            estimated_cost_usd=state.estimated_cost_usd,
            budget_exhausted=(state.stopped_reason == "budget_exhausted"),
        )

    def _effective_tool_schemas(
        self,
        base_tool_schemas: list[dict[str, Any]],
        resolved_policy: ResolvedPolicy,
        state: LoopState,
        tool_format: str,
    ) -> list[dict[str, Any]]:
        if state.active_tool_overrides:
            return self.tool_executor.available_tool_schemas_with_overrides(
                policy=resolved_policy,
                overrides=state.active_tool_overrides,
                format=tool_format,
            )
        if state.tool_schemas_dirty:
            state.tool_schemas_dirty = False
            recomputed = self.tool_executor.available_tool_schemas(policy=resolved_policy, format=tool_format)
            return recomputed if recomputed else list(base_tool_schemas)
        return list(base_tool_schemas)

    def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
        context: ToolContext,
        resolved_policy: ResolvedPolicy,
    ) -> list[ToolCallResult]:
        if (
            self.config.parallel_read_tools
            and tool_calls
            and all(self.tool_executor.get_action_type(call.name) in READ_ONLY_ACTIONS for call in tool_calls)
        ):
            workers = max(1, self.config.max_parallel_workers)
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bomba-loop-tools") as pool:
                futures = [
                    pool.submit(
                        self.tool_executor.execute,
                        call.name,
                        call.arguments,
                        context,
                        resolved_policy,
                        1.0,
                        call.id,
                    )
                    for call in tool_calls
                ]
                out: list[ToolCallResult] = []
                for idx, future in enumerate(futures):
                    try:
                        out.append(future.result())
                    except Exception as exc:  # pragma: no cover - defensive path
                        call = tool_calls[idx]
                        out.append(
                            ToolCallResult(
                                tool_call_id=call.id,
                                tool_name=call.name,
                                status="error",
                                output={"error": str(exc)},
                                risk_class="unknown",
                                duration_ms=0,
                            )
                        )
                return out

        results: list[ToolCallResult] = []
        for call in tool_calls:
            result = self.tool_executor.execute(
                tool_name=call.name,
                arguments=call.arguments,
                context=context,
                policy=resolved_policy,
                confidence=1.0,
                tool_call_id=call.id,
            )
            results.append(result)
        return results

    def _inject_health_as_message(self, state: LoopState, model_id: str) -> None:
        if state.iteration <= 1:
            return
        health = build_health_snapshot(state, self.config, model_id)
        health_msg = ChatMessage(role="user", content=health.as_system_text())
        if state.health_message_idx is not None and state.health_message_idx < len(state.messages):
            state.messages[state.health_message_idx] = health_msg
            return
        state.health_message_idx = len(state.messages)
        state.messages.append(health_msg)

    def _parse_tool_calls(self, response: LLMResponse) -> list[ToolCall]:
        raw = response.raw
        calls: list[ToolCall] = []

        choices = raw.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict) and isinstance(message.get("tool_calls"), list):
                for item in message.get("tool_calls") or []:
                    if not isinstance(item, dict):
                        continue
                    function = item.get("function")
                    if not isinstance(function, dict):
                        continue
                    name = str(function.get("name") or "")
                    args_raw = function.get("arguments")
                    if not name:
                        continue
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) and args_raw else {}
                    except json.JSONDecodeError:
                        args = {}
                    calls.append(
                        ToolCall(
                            id=str(item.get("id") or uuid.uuid4()),
                            name=name,
                            arguments=(args if isinstance(args, dict) else {}),
                        )
                    )
                return calls

        content = raw.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                name = str(block.get("name") or "")
                if not name:
                    continue
                input_payload = block.get("input")
                calls.append(
                    ToolCall(
                        id=str(block.get("id") or uuid.uuid4()),
                        name=name,
                        arguments=(input_payload if isinstance(input_payload, dict) else {}),
                    )
                )
        return calls

    def _assistant_and_tool_messages(
        self,
        response: LLMResponse,
        tool_calls: list[ToolCall],
        results: list[ToolCallResult],
    ) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        openai_mode = isinstance(response.raw.get("choices"), list)

        if openai_mode:
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=response.text or "",
                    tool_calls=[
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                        }
                        for call in tool_calls
                    ],
                )
            )
            for result in results:
                messages.append(
                    ChatMessage(
                        role="tool",
                        content=json.dumps(result.output, ensure_ascii=True),
                        tool_call_id=result.tool_call_id,
                    )
                )
            return messages

        assistant_blocks: list[dict[str, Any]] = []
        if response.text:
            assistant_blocks.append({"type": "text", "text": response.text})
        for call in tool_calls:
            assistant_blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
        messages.append(ChatMessage(role="assistant", content=assistant_blocks))
        tool_blocks = [
            {
                "type": "tool_result",
                "tool_use_id": result.tool_call_id,
                "content": json.dumps(result.output, ensure_ascii=True),
            }
            for result in results
        ]
        messages.append(ChatMessage(role="user", content=tool_blocks))
        return messages

    def _detect_loop(self, state: LoopState) -> bool:
        window = self.config.loop_detection_window
        if window < 2:
            return False
        if len(state.tool_calls_history) < window:
            return False
        recent = state.tool_calls_history[-window:]
        signatures = [
            (item.tool_name, json.dumps(item.output, sort_keys=True, ensure_ascii=True), item.status)
            for item in recent
        ]
        return len(set(signatures)) == 1

    @staticmethod
    def _accumulate_usage(response: LLMResponse, state: LoopState) -> tuple[int, int]:
        usage = response.usage or {}
        input_tokens = int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("input")
            or 0
        )
        output_tokens = int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("output")
            or 0
        )
        state.total_input_tokens += input_tokens
        state.total_output_tokens += output_tokens
        return input_tokens, output_tokens
