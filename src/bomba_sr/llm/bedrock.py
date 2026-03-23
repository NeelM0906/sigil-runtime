"""Amazon Bedrock provider using boto3. HIPAA-eligible when BAA is signed."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from bomba_sr.llm.providers import ChatMessage, LLMResponse


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
    """

    access_key: str
    secret_key: str
    region: str = "us-east-1"
    provider_name: str = "bedrock"

    def _client(self):
        import boto3
        return boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def generate(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        # Normalize model ID: add us. prefix for cross-region inference
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

        payload: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": api_messages if api_messages else [{"role": "user", "content": ""}],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if tools:
            payload["tools"] = tools

        client = self._client()
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

        return LLMResponse(
            text=text,
            model=model_id,
            usage=usage_dict,
            raw=body,
            stop_reason=stop_reason,
        )

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
