from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


def default_embedding_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or None


def default_embedding_model() -> str:
    if os.getenv("OPENAI_EMBEDDING_MODEL"):
        return os.environ["OPENAI_EMBEDDING_MODEL"]
    # Use OpenAI model name directly (not openrouter-prefixed) since
    # embeddings go to OpenAI API when OPENAI_API_KEY is set
    return "text-embedding-3-small"


def default_embedding_api_base() -> str:
    if os.getenv("OPENAI_BASE_URL"):
        return os.environ["OPENAI_BASE_URL"]
    # If we have an OpenAI key, use OpenAI directly for embeddings
    # (OpenRouter doesn't reliably proxy embedding endpoints)
    if os.getenv("OPENAI_API_KEY"):
        return "https://api.openai.com/v1"
    if os.getenv("OPENROUTER_API_KEY"):
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return "https://api.openai.com/v1"


@dataclass
class OpenAIEmbeddingProvider:
    api_key: str
    model: str = default_embedding_model()
    api_base: str = default_embedding_api_base()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # OpenAI text-embedding-3-small has ~8191 token limit (~30K chars).
        # Truncate oversized inputs to avoid 400 errors.
        truncated = [t[:30000] if len(t) > 30000 else t for t in texts]
        payload = {
            "model": self.model,
            "input": truncated,
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
        with urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))

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
