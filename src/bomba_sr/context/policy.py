from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


def estimate_tokens(text: str) -> int:
    # Stable heuristic used throughout the runtime when tokenizer APIs are unavailable.
    return max(1, (len(text) + 3) // 4)


class TurnProfile(StrEnum):
    CHAT = "chat"
    TASK_EXECUTION = "task_execution"
    PLANNING = "planning"
    MEMORY_RECALL = "memory_recall"
    SUBAGENT_ORCHESTRATION = "subagent_orchestration"


@dataclass(frozen=True)
class ContextBudget:
    model_context_length: int
    reserved_output_tokens: int
    reserved_safety_tokens: int
    available_input_tokens: int


@dataclass
class ContextAssemblyResult:
    context_text: str
    final_input_tokens: int
    compressed: bool
    included_sections: list[str]
    dropped_sections: list[str]
    compression_summary: dict[str, Any]


PROFILE_WEIGHTS: dict[TurnProfile, dict[str, float]] = {
    TurnProfile.CHAT: {
        "working_memory": 0.26,
        "world_state": 0.08,
        "semantic": 0.24,
        "recent_history": 0.34,
        "procedural": 0.05,
        "predictions": 0.03,
    },
    TurnProfile.TASK_EXECUTION: {
        "working_memory": 0.34,
        "world_state": 0.10,
        "semantic": 0.18,
        "recent_history": 0.20,
        "procedural": 0.12,
        "predictions": 0.06,
    },
    TurnProfile.PLANNING: {
        "working_memory": 0.24,
        "world_state": 0.15,
        "semantic": 0.22,
        "recent_history": 0.17,
        "procedural": 0.18,
        "predictions": 0.04,
    },
    TurnProfile.MEMORY_RECALL: {
        "working_memory": 0.12,
        "world_state": 0.08,
        "semantic": 0.42,
        "recent_history": 0.26,
        "procedural": 0.06,
        "predictions": 0.06,
    },
    TurnProfile.SUBAGENT_ORCHESTRATION: {
        "working_memory": 0.28,
        "world_state": 0.10,
        "semantic": 0.18,
        "recent_history": 0.14,
        "procedural": 0.12,
        "predictions": 0.18,
    },
}


def calculate_budget(model_context_length: int) -> ContextBudget:
    reserved_output_tokens = min(32000, int(model_context_length * 0.20))
    reserved_safety_tokens = max(2000, int(model_context_length * 0.03))
    available = model_context_length - reserved_output_tokens - reserved_safety_tokens
    if available <= 0:
        raise ValueError("Invalid context budget; no input tokens available")
    return ContextBudget(
        model_context_length=model_context_length,
        reserved_output_tokens=reserved_output_tokens,
        reserved_safety_tokens=reserved_safety_tokens,
        available_input_tokens=available,
    )


class ContextPolicyEngine:
    def assemble(
        self,
        profile: TurnProfile,
        model_context_length: int,
        system_contract: str,
        user_message: str,
        inputs: dict[str, Any],
    ) -> ContextAssemblyResult:
        budget = calculate_budget(model_context_length)
        included: list[str] = []
        dropped: list[str] = []
        compression_summary: dict[str, Any] = {
            "summarized": [],
            "truncated": [],
            "dropped": [],
        }

        required_blocks: list[tuple[str, str]] = [
            ("system_contract", system_contract.strip()),
            ("user_message", user_message.strip()),
        ]

        explicit_constraints = inputs.get("explicit_user_constraints") or []
        if explicit_constraints:
            constraints_text = "\n".join(f"- {c}" for c in explicit_constraints)
            required_blocks.append(("explicit_constraints", constraints_text))

        task_state = inputs.get("task_state")
        if task_state:
            required_blocks.append(("task_state", self._normalize_item(task_state)))

        tool_results = inputs.get("tool_results") or []
        if tool_results:
            # Preserve source provenance for tool outputs even when full tool payloads are compressed.
            tool_lines: list[str] = []
            for item in tool_results:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source") or "").strip()
                text = str(item.get("text") or item.get("content") or "").strip()
                if source:
                    if text:
                        tool_lines.append(f"[source: {source}] {text}")
                    else:
                        tool_lines.append(f"[source: {source}]")
            if tool_lines:
                required_blocks.append(("tool_provenance", "\n".join(tool_lines)))

        required_text = self._join_blocks(required_blocks)
        required_tokens = estimate_tokens(required_text)
        if required_tokens > budget.available_input_tokens:
            # Required sections cannot be dropped. Summarize required content minimally.
            required_text = self._summarize(required_text, budget.available_input_tokens)
            required_tokens = estimate_tokens(required_text)
            compression_summary["summarized"].append("required")

        remaining = max(0, budget.available_input_tokens - required_tokens)

        weights = PROFILE_WEIGHTS[profile]
        optional_blocks: list[tuple[str, str]] = []

        optional_sources = [
            ("working_memory", inputs.get("working_memory", [])),
            ("world_state", [inputs.get("world_state", {})]),
            ("semantic", inputs.get("semantic_candidates", [])),
            ("recent_history", inputs.get("recent_history", [])),
            ("procedural", inputs.get("procedural_candidates", [])),
            ("predictions", inputs.get("pending_predictions", [])),
        ]

        for name, items in optional_sources:
            allocation = int(remaining * weights[name])
            block_text = self._pack_items(name, items, allocation, compression_summary)
            if block_text:
                optional_blocks.append((name, block_text))
                included.append(name)
            else:
                dropped.append(name)
                compression_summary["dropped"].append(name)

        final_text = self._join_blocks(required_blocks + optional_blocks)
        final_tokens = estimate_tokens(final_text)
        compressed = final_tokens > budget.available_input_tokens

        if compressed:
            # Final safety pass.
            final_text = self._summarize(final_text, budget.available_input_tokens)
            final_tokens = estimate_tokens(final_text)
            compression_summary["summarized"].append("final_safety_pass")

        # Invariant checks.
        self._assert_constraints_kept(final_text, explicit_constraints)
        self._assert_tool_sources_preserved(final_text, inputs)
        self._assert_contradiction_labels(final_text)

        included = ["system_contract", "user_message"] + (["explicit_constraints"] if explicit_constraints else []) + included
        if task_state:
            included.insert(2, "task_state")

        return ContextAssemblyResult(
            context_text=final_text,
            final_input_tokens=final_tokens,
            compressed=bool(compression_summary["summarized"] or compression_summary["truncated"] or compression_summary["dropped"]),
            included_sections=included,
            dropped_sections=dropped,
            compression_summary=compression_summary,
        )

    @staticmethod
    def should_trigger_pre_compaction_flush(
        token_estimate: int,
        context_window: int,
        reserve_tokens_floor: int = 20000,
        soft_threshold_tokens: int = 4000,
    ) -> bool:
        threshold = context_window - reserve_tokens_floor - soft_threshold_tokens
        return token_estimate >= threshold

    def _pack_items(
        self,
        name: str,
        items: list[Any],
        token_budget: int,
        compression_summary: dict[str, Any],
    ) -> str:
        if token_budget <= 0 or not items:
            return ""

        texts: list[str] = []
        used = 0
        for item in items:
            normalized = self._normalize_item(item)
            if not normalized:
                continue
            item_tokens = estimate_tokens(normalized)
            if used + item_tokens <= token_budget:
                texts.append(normalized)
                used += item_tokens
                continue

            if token_budget - used > 12:
                summarized = self._summarize(normalized, token_budget - used)
                texts.append(summarized)
                used += estimate_tokens(summarized)
                compression_summary["summarized"].append(name)
            else:
                compression_summary["truncated"].append(name)
            break

        if not texts:
            return ""
        return "\n".join(texts)

    @staticmethod
    def _normalize_item(item: Any) -> str:
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("content") or "").strip()
            source = str(item.get("source") or "").strip()
            recency = str(item.get("recency_label") or "").strip()
            contradictory = bool(item.get("contradictory") or False)
            pieces = []
            if source:
                pieces.append(f"[source: {source}]")
            if recency:
                pieces.append(f"[recency: {recency}]")
            if contradictory:
                pieces.append("[contradiction_state: present]")
            if text:
                pieces.append(text)
            return " ".join(pieces).strip()
        return str(item).strip()

    @staticmethod
    def _summarize(text: str, max_tokens: int) -> str:
        if max_tokens <= 8:
            return ""
        max_chars = max_tokens * 4
        clean = text.strip()
        if len(clean) <= max_chars:
            return clean
        head = clean[: max_chars // 2]
        tail = clean[-(max_chars // 3) :]
        return f"{head}\n...[summary-compression]...\n{tail}"

    @staticmethod
    def _join_blocks(blocks: list[tuple[str, str]]) -> str:
        chunks: list[str] = []
        for name, text in blocks:
            if not text:
                continue
            chunks.append(f"## {name}\n{text}")
        return "\n\n".join(chunks).strip()

    @staticmethod
    def _assert_constraints_kept(context_text: str, constraints: list[str]) -> None:
        for constraint in constraints:
            if constraint and constraint not in context_text:
                raise AssertionError("Explicit user constraint dropped during context assembly")

    @staticmethod
    def _assert_tool_sources_preserved(context_text: str, inputs: dict[str, Any]) -> None:
        tool_results = inputs.get("tool_results") or []
        for item in tool_results:
            if isinstance(item, dict) and item.get("source"):
                source = str(item["source"])
                if source not in context_text:
                    raise AssertionError("Tool output source reference missing after compression")

    @staticmethod
    def _assert_contradiction_labels(context_text: str) -> None:
        if "contradiction_state" in context_text and "recency:" not in context_text:
            raise AssertionError("Contradictory memory included without recency labeling")
