"""Amazon Bedrock provider using boto3. HIPAA-eligible when BAA is signed."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMResponse

log = logging.getLogger(__name__)

# Model context windows (input tokens). Conservative estimates.
_MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-4": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-haiku": 200_000,
}

_DEFAULT_CONTEXT_LIMIT = 200_000
_CHARS_PER_TOKEN = 4  # conservative estimate


_BEDROCK_MODEL_ALIASES: dict[str, str] = {
    "anthropic/claude-opus-4.6": "us.anthropic.claude-opus-4-6-v1",
    "anthropic/claude-opus-4-6": "us.anthropic.claude-opus-4-6-v1",
    "anthropic/claude-sonnet-4.6": "us.anthropic.claude-sonnet-4-6",
    "anthropic/claude-sonnet-4-6": "us.anthropic.claude-sonnet-4-6",
    "anthropic/claude-haiku-4.5": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic/claude-haiku-4-5": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic/claude-sonnet-4-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic/claude-3-5-sonnet-20241022": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic/claude-3-haiku-20240307": "us.anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-haiku-4.5": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic/claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
}


@dataclass
class BedrockProvider:
    """LLM provider for Amazon Bedrock via boto3.

    Uses cross-region inference profiles (us.anthropic.* model IDs).
    Includes retry with exponential backoff for throttling.
    """

    access_key: str
    secret_key: str
    region: str = "us-east-1"
    provider_name: str = "bedrock"
    max_output_tokens: int = 8192
    max_retries: int = 3
    _client_cache: Any = field(default=None, repr=False)

    def _client(self):
        if self._client_cache is None:
            import boto3
            from botocore.config import Config
            self._client_cache = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    retries={"max_attempts": 0},  # we handle retries ourselves
                    read_timeout=120,
                    connect_timeout=10,
                ),
            )
        return self._client_cache

    def _estimate_input_tokens(self, payload: dict) -> int:
        """Rough estimate of input token count from payload."""
        raw = json.dumps(payload)
        return len(raw) // _CHARS_PER_TOKEN

    def _context_limit_for_model(self, model_id: str) -> int:
        """Get the context window limit for a model."""
        for prefix, limit in _MODEL_CONTEXT_LIMITS.items():
            if prefix in model_id:
                return limit
        return _DEFAULT_CONTEXT_LIMIT

    def generate(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        model_id = self._normalize_model_id(model)

        # Build Anthropic Messages API payload
        system_parts: list[str] = []
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                text = str(msg.content) if isinstance(msg.content, str) else json.dumps(msg.content)
                system_parts.append(text)
                continue
            role = "assistant" if msg.role == "assistant" else "user"
            entry: dict[str, Any] = {"role": role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            api_messages.append(entry)

        # Determine max_tokens: use configured value, capped by context limit
        context_limit = self._context_limit_for_model(model_id)
        max_tokens = self.max_output_tokens

        payload: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": api_messages if api_messages else [{"role": "user", "content": ""}],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if tools:
            payload["tools"] = [self._convert_tool(t) for t in tools]

        # Pre-flight: estimate input size and warn/truncate if too large
        est_input = self._estimate_input_tokens(payload)
        if est_input + max_tokens > context_limit:
            log.warning(
                "[bedrock] Input estimate %d + max_tokens %d exceeds context %d for %s. "
                "Reducing max_tokens to fit.",
                est_input, max_tokens, context_limit, model_id,
            )
            max_tokens = max(256, context_limit - est_input - 1000)  # 1K safety margin
            payload["max_tokens"] = max_tokens
            if max_tokens <= 256:
                log.error(
                    "[bedrock] Prompt too large (%d est tokens) for %s context (%d). "
                    "Truncating messages.",
                    est_input, model_id, context_limit,
                )
                # Truncate from the middle: keep first 2 and last 3 messages
                if len(api_messages) > 5:
                    payload["messages"] = api_messages[:2] + api_messages[-3:]
                    payload["max_tokens"] = 4096

        # Invoke with retry + exponential backoff for throttling
        client = self._client()
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload),
                )
                body = json.loads(resp["body"].read())

                # Parse Anthropic Messages response
                text = ""
                for item in body.get("content") or []:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text += str(item.get("text") or "")
                stop_reason = str(body.get("stop_reason")) if body.get("stop_reason") else None

                usage = body.get("usage") if isinstance(body.get("usage"), dict) else None
                usage_dict = None
                if usage:
                    usage_dict = {k: int(v) for k, v in usage.items() if isinstance(v, (int, float))}

                if attempt > 1:
                    log.info("[bedrock] Succeeded on attempt %d for %s", attempt, model_id)

                return LLMResponse(
                    text=text,
                    model=model_id,
                    usage=usage_dict,
                    raw=body,
                    stop_reason=stop_reason,
                )

            except Exception as exc:
                last_exc = exc
                exc_type = type(exc).__name__
                exc_str = str(exc)

                # Identify retryable errors
                is_throttle = "ThrottlingException" in exc_type or "ThrottlingException" in exc_str
                is_timeout = "ReadTimeoutError" in exc_type or "timed out" in exc_str.lower()
                is_service = "ServiceUnavailableException" in exc_type or "500" in exc_str
                is_retryable = is_throttle or is_timeout or is_service

                if not is_retryable or attempt == self.max_retries:
                    log.error(
                        "[bedrock] %s on attempt %d/%d for %s: %s",
                        exc_type, attempt, self.max_retries, model_id, exc_str[:300],
                    )
                    break

                # Exponential backoff: 2s, 4s, 8s
                delay = 2 ** attempt
                log.warning(
                    "[bedrock] %s on attempt %d/%d for %s — retrying in %ds",
                    exc_type, attempt, self.max_retries, model_id, delay,
                )
                time.sleep(delay)

        raise RuntimeError(
            f"Bedrock call failed after {self.max_retries} attempts for {model_id}: {last_exc}"
        )

    @staticmethod
    def _convert_tool(tool: dict[str, Any]) -> dict[str, Any]:
        """Convert OpenAI tool format to Anthropic tool format for Bedrock.

        OpenAI: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        Anthropic: {"name": ..., "description": ..., "input_schema": ...}
        """
        if tool.get("type") == "function" and "function" in tool:
            fn = tool["function"]
            return {
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        # Already in Anthropic format or unknown — pass through
        return tool

    @staticmethod
    def _normalize_model_id(model: str) -> str:
        """Normalize model ID for Bedrock cross-region inference.

        Bedrock requires 'us.' prefix for cross-region inference profiles.
        Handles common input formats:
          anthropic/claude-opus-4.6      → us.anthropic.claude-opus-4-6-v1
          anthropic.claude-opus-4-6-v1   → us.anthropic.claude-opus-4-6-v1
          us.anthropic.claude-opus-4-6-v1 → unchanged
        """
        # Check alias table first
        if model in _BEDROCK_MODEL_ALIASES:
            return _BEDROCK_MODEL_ALIASES[model]

        # Already has region prefix
        if model.startswith("us.") or model.startswith("eu."):
            return model

        # OpenRouter-style: anthropic/claude-opus-4.6
        if "/" in model:
            model = model.split("/", 1)[1]
            # Convert dots in version to hyphens: claude-opus-4.6 → claude-opus-4-6
            model = model.replace(".", "-")
            # Add version suffix if missing
            if not model.endswith("-v1") and not model.endswith("-v1:0"):
                model = f"{model}-v1"
            return f"us.anthropic.{model}"

        # Already Bedrock-style: anthropic.claude-opus-4-6-v1
        if model.startswith("anthropic."):
            return f"us.{model}"

        # Raw model name: claude-opus-4-6-v1
        return f"us.anthropic.{model}"
