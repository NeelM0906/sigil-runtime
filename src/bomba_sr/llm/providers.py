from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str | list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    usage: dict[str, int] | None
    raw: dict[str, Any]
    stop_reason: str | None = None


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, model: str, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        raise NotImplementedError


@dataclass
class OpenAICompatibleProvider:
    provider_name: str
    api_key: str
    api_base: str

    def generate(self, model: str, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [self._message_dict(m) for m in messages],
        }
        if tools:
            payload["tools"] = tools

        req = Request(
            url=f"{self.api_base.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = ""
            try:
                details = exc.read().decode("utf-8")
            except Exception:
                details = ""
            hint = ""
            if exc.code in {401, 403}:
                hint = " Check OPENROUTER_API_KEY / OPENAI_API_KEY and base URL."
            provider_label = self.provider_name
            raise RuntimeError(f"{provider_label} request failed ({exc.code}): {details or exc.reason}.{hint}") from exc

        choices = body.get("choices") or []
        text = ""
        stop_reason = None
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            text = str(message.get("content") or "")
            stop_reason = str(choices[0].get("finish_reason")) if choices[0].get("finish_reason") is not None else None

        usage = body.get("usage") if isinstance(body.get("usage"), dict) else None
        usage_dict = None
        if usage is not None:
            usage_dict = {k: int(v) for k, v in usage.items() if isinstance(v, (int, float))}

        return LLMResponse(
            text=text,
            model=str(body.get("model") or model),
            usage=usage_dict,
            raw=body,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _message_dict(message: ChatMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.tool_calls:
            payload["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        return payload


@dataclass
class AnthropicProvider:
    api_key: str
    api_base: str = "https://api.anthropic.com/v1"
    provider_name: str = "anthropic"

    def generate(self, model: str, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        system_chunks = [str(m.content) for m in messages if m.role == "system"]
        api_messages: list[dict[str, Any]] = []
        for item in messages:
            if item.role == "system":
                continue
            role = "assistant" if item.role == "assistant" else "user"
            payload: dict[str, Any] = {"role": role, "content": item.content}
            if item.tool_calls:
                payload["tool_calls"] = item.tool_calls
            api_messages.append(payload)

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "system": "\n\n".join(system_chunks),
            "messages": api_messages if api_messages else [{"role": "user", "content": ""}],
        }
        if tools:
            payload["tools"] = tools

        req = Request(
            url=f"{self.api_base.rstrip('/')}/messages",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": self.api_key,
            },
        )
        try:
            with urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = ""
            try:
                details = exc.read().decode("utf-8")
            except Exception:
                details = ""
            hint = ""
            if exc.code in {401, 403}:
                hint = " Check ANTHROPIC_API_KEY."
            raise RuntimeError(f"anthropic request failed ({exc.code}): {details or exc.reason}.{hint}") from exc

        text = ""
        for item in body.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                text += str(item.get("text") or "")
        stop_reason = str(body.get("stop_reason")) if body.get("stop_reason") is not None else None

        usage = body.get("usage") if isinstance(body.get("usage"), dict) else None
        usage_dict = None
        if usage is not None:
            usage_dict = {k: int(v) for k, v in usage.items() if isinstance(v, (int, float))}

        return LLMResponse(
            text=text,
            model=str(body.get("model") or model),
            usage=usage_dict,
            raw=body,
            stop_reason=stop_reason,
        )


@dataclass
class StaticEchoProvider:
    provider_name: str = "static_echo"

    def generate(self, model: str, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        last_user = ""
        for message in reversed(messages):
            if message.role == "user":
                if isinstance(message.content, str):
                    last_user = message.content
                else:
                    last_user = json.dumps(message.content)
                break
        response = f"[echo:{model}] {last_user[:500]}"
        return LLMResponse(
            text=response,
            model=model,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            raw={"echo": True},
            stop_reason="stop",
        )


def provider_from_env() -> LLMProvider:
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])

    if os.getenv("OPENAI_API_KEY"):
        return OpenAICompatibleProvider(
            provider_name="openai",
            api_key=os.environ["OPENAI_API_KEY"],
            api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    if os.getenv("OPENROUTER_API_KEY"):
        return OpenAICompatibleProvider(
            provider_name="openrouter",
            api_key=os.environ["OPENROUTER_API_KEY"],
            api_base=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )

    return StaticEchoProvider()
