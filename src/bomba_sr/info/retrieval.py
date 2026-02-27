from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RetrievalSnippet:
    title: str
    source_url: str
    snippet: str
    confidence: float


class GenericInfoRetriever:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def is_generic_query(self, text: str) -> bool:
        query = text.strip().lower()
        patterns = [
            r"^what is\b",
            r"^who is\b",
            r"^when did\b",
            r"^tell me about\b",
            r"^explain\b",
            r"^how does\b",
            r"\bmeaning of\b",
            r"\bdefinition of\b",
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    def retrieve(self, query: str, limit: int = 2) -> list[RetrievalSnippet]:
        if not self.enabled:
            return []

        title = self._resolve_wikipedia_title(query)
        if title is None:
            return []

        summary = self._fetch_wikipedia_summary(title)
        if summary is None:
            return []

        return [
            RetrievalSnippet(
                title=summary["title"],
                source_url=summary["source_url"],
                snippet=summary["snippet"],
                confidence=0.78,
            )
        ][:limit]

    def _resolve_wikipedia_title(self, query: str) -> str | None:
        endpoint = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=opensearch&search={quote(query)}&limit=1&namespace=0&format=json"
        )
        req = Request(endpoint, method="GET", headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        if not isinstance(body, list) or len(body) < 2:
            return None
        titles = body[1]
        if not isinstance(titles, list) or not titles:
            return None
        title = titles[0]
        if not isinstance(title, str) or not title.strip():
            return None
        return title

    def _fetch_wikipedia_summary(self, title: str) -> dict[str, Any] | None:
        endpoint = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
        req = Request(endpoint, method="GET", headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        extract = body.get("extract") if isinstance(body, dict) else None
        page_title = body.get("title") if isinstance(body, dict) else None
        content_urls = body.get("content_urls") if isinstance(body, dict) else None
        desktop = None
        if isinstance(content_urls, dict):
            desktop = content_urls.get("desktop")
        page_url = None
        if isinstance(desktop, dict):
            page_url = desktop.get("page")

        if not isinstance(extract, str) or not extract.strip():
            return None
        if not isinstance(page_title, str):
            page_title = title
        if not isinstance(page_url, str):
            page_url = f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}"

        return {
            "title": page_title,
            "source_url": page_url,
            "snippet": extract.strip()[:900],
        }
