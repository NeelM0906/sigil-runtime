from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


@dataclass
class OpenAIEmbeddingProvider:
    api_key: str
    model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    api_base: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self.model,
            "input": texts,
        }
        req = Request(
            url=f"{self.api_base.rstrip('/')}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = ""
            try:
                details = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            log.warning("Embedding API error %d: %s", exc.code, details[:300] or exc.reason)
            return [[] for _ in texts]
        except Exception as exc:
            log.warning("Embedding request failed: %s", exc)
            return [[] for _ in texts]

        data = body.get("data")
        if not isinstance(data, list):
            raise RuntimeError("Invalid embeddings response: missing data")

        vectors: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list):
                raise RuntimeError("Invalid embeddings response: embedding missing")
            vectors.append([float(x) for x in embedding])
        return vectors
