from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.request import Request, urlopen

from bomba_sr.storage.db import RuntimeDB, dict_from_row


class CapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelCapabilities:
    model_id: str
    context_length: int
    max_completion_tokens: int
    supports_tools: bool
    supports_json_mode: bool
    provider_context_length: int | None
    raw_metadata: dict[str, Any]
    fetched_at: datetime
    expires_at: datetime


class ModelCapabilityService:
    def __init__(
        self,
        db: RuntimeDB,
        api_base: str = "https://openrouter.ai/api/v1",
        api_key: str | None = None,
        cache_ttl_seconds: int = 6 * 60 * 60,
        fetcher: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.db = db
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self._fetcher = fetcher
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS model_capabilities_cache (
              model_id TEXT PRIMARY KEY,
              context_length INTEGER NOT NULL,
              max_completion_tokens INTEGER NOT NULL,
              supports_tools INTEGER NOT NULL,
              supports_json_mode INTEGER NOT NULL,
              provider_context_length INTEGER,
              raw_metadata TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              expires_at TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    def get_capabilities(
        self,
        model_id: str,
        force_refresh: bool = False,
        now: datetime | None = None,
    ) -> ModelCapabilities:
        current = now or datetime.now(timezone.utc)
        if not force_refresh:
            cached = self._get_cached(model_id, current)
            if cached is not None:
                return cached
        discovered = self._discover_model_capabilities(model_id)
        return self._save_cache(discovered, current)

    def _get_cached(self, model_id: str, now: datetime) -> ModelCapabilities | None:
        row = self.db.execute(
            "SELECT * FROM model_capabilities_cache WHERE model_id = ?",
            (model_id,),
        ).fetchone()
        if row is None:
            return None
        record = dict_from_row(row)
        if record is None:
            return None
        expires_at = datetime.fromisoformat(record["expires_at"])
        if expires_at <= now:
            return None
        return self._row_to_caps(record)

    def _save_cache(self, caps: ModelCapabilities, now: datetime) -> ModelCapabilities:
        expires_at = now + timedelta(seconds=self.cache_ttl_seconds)
        self.db.execute(
            """
            INSERT INTO model_capabilities_cache (
              model_id, context_length, max_completion_tokens, supports_tools,
              supports_json_mode, provider_context_length, raw_metadata,
              fetched_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_id) DO UPDATE SET
              context_length=excluded.context_length,
              max_completion_tokens=excluded.max_completion_tokens,
              supports_tools=excluded.supports_tools,
              supports_json_mode=excluded.supports_json_mode,
              provider_context_length=excluded.provider_context_length,
              raw_metadata=excluded.raw_metadata,
              fetched_at=excluded.fetched_at,
              expires_at=excluded.expires_at
            """,
            (
                caps.model_id,
                caps.context_length,
                caps.max_completion_tokens,
                int(caps.supports_tools),
                int(caps.supports_json_mode),
                caps.provider_context_length,
                json.dumps(caps.raw_metadata, separators=(",", ":")),
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        self.db.commit()
        return ModelCapabilities(
            model_id=caps.model_id,
            context_length=caps.context_length,
            max_completion_tokens=caps.max_completion_tokens,
            supports_tools=caps.supports_tools,
            supports_json_mode=caps.supports_json_mode,
            provider_context_length=caps.provider_context_length,
            raw_metadata=caps.raw_metadata,
            fetched_at=now,
            expires_at=expires_at,
        )

    def _discover_model_capabilities(self, model_id: str) -> ModelCapabilities:
        models = self._fetch_models()
        model = next((m for m in models if m.get("id") == model_id), None)
        if model is None:
            raise CapabilityError(f"Model not found in catalog: {model_id}")

        top_provider = model.get("top_provider") or {}
        context_length = int(top_provider.get("context_length") or model.get("context_length") or 0)
        max_completion = int(top_provider.get("max_completion_tokens") or 0)
        if context_length < 8192:
            raise CapabilityError(f"Invalid context length for {model_id}: {context_length}")
        if max_completion < 256:
            # Sensible fallback: reserve 1/8 of context for output where provider omits cap.
            max_completion = max(256, context_length // 8)

        supported = [str(x).lower() for x in (model.get("supported_parameters") or [])]
        supports_tools = any(x in supported for x in ("tools", "tool_choice"))
        supports_json_mode = any(x in supported for x in ("response_format", "structured_outputs"))

        now = datetime.now(timezone.utc)
        return ModelCapabilities(
            model_id=model_id,
            context_length=context_length,
            max_completion_tokens=max_completion,
            supports_tools=supports_tools,
            supports_json_mode=supports_json_mode,
            provider_context_length=(int(top_provider["context_length"]) if top_provider.get("context_length") else None),
            raw_metadata=model,
            fetched_at=now,
            expires_at=now + timedelta(seconds=self.cache_ttl_seconds),
        )

    def _fetch_models(self) -> list[dict[str, Any]]:
        if self._fetcher is not None:
            return self._fetcher()

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = Request(url=f"{self.api_base}/models", headers=headers, method="GET")
        with urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("data")
        if not isinstance(models, list):
            raise CapabilityError("Invalid models payload: missing data list")
        return models

    @staticmethod
    def _row_to_caps(row: dict[str, Any]) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=str(row["model_id"]),
            context_length=int(row["context_length"]),
            max_completion_tokens=int(row["max_completion_tokens"]),
            supports_tools=bool(int(row["supports_tools"])),
            supports_json_mode=bool(int(row["supports_json_mode"])),
            provider_context_length=(int(row["provider_context_length"]) if row["provider_context_length"] is not None else None),
            raw_metadata=json.loads(row["raw_metadata"]),
            fetched_at=datetime.fromisoformat(str(row["fetched_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])),
        )
