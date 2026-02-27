from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


def _http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sigil-runtime/1.0",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("content-type", "")
        return resp.read(), content_type


def _html_to_text(value: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", "", value)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", "", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _web_search_factory(brave_api_key: str | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        _ = context
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(10, int(arguments.get("limit") or 5)))

        if brave_api_key:
            q = urllib.parse.quote_plus(query)
            url = f"https://api.search.brave.com/res/v1/web/search?q={q}&count={limit}"
            payload_bytes, _ = _http_get(url, headers={"X-Subscription-Token": brave_api_key})
            payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))
            web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
            items = web.get("results") if isinstance(web.get("results"), list) else []
            results = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                results.append(
                    {
                        "title": str(item.get("title") or ""),
                        "url": str(item.get("url") or ""),
                        "snippet": str(item.get("description") or ""),
                    }
                )
            return {"provider": "brave", "query": query, "results": results}

        q = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&no_redirect=1"
        payload_bytes, _ = _http_get(url)
        payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))

        results: list[dict[str, str]] = []
        abstract_url = str(payload.get("AbstractURL") or "")
        abstract = str(payload.get("Abstract") or "")
        heading = str(payload.get("Heading") or query)
        if abstract_url and abstract:
            results.append({"title": heading, "url": abstract_url, "snippet": abstract})

        related = payload.get("RelatedTopics")
        if isinstance(related, list):
            for item in related:
                if len(results) >= limit:
                    break
                if not isinstance(item, dict):
                    continue
                if "Text" in item and "FirstURL" in item:
                    results.append(
                        {
                            "title": str(item.get("Text") or "")[:120],
                            "url": str(item.get("FirstURL") or ""),
                            "snippet": str(item.get("Text") or ""),
                        }
                    )
                    continue
                topics = item.get("Topics")
                if isinstance(topics, list):
                    for nested in topics:
                        if len(results) >= limit:
                            break
                        if not isinstance(nested, dict):
                            continue
                        if "Text" in nested and "FirstURL" in nested:
                            results.append(
                                {
                                    "title": str(nested.get("Text") or "")[:120],
                                    "url": str(nested.get("FirstURL") or ""),
                                    "snippet": str(nested.get("Text") or ""),
                                }
                            )

        return {"provider": "duckduckgo", "query": query, "results": results[:limit]}

    return run


def _web_fetch(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    url = str(arguments.get("url") or "").strip()
    if not url:
        raise ValueError("url is required")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http or https")

    payload_bytes, content_type = _http_get(url)
    text = payload_bytes.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or text.lstrip().startswith("<"):
        text = _html_to_text(text)

    max_chars = max(500, min(100000, int(arguments.get("max_chars") or 20000)))
    return {
        "url": url,
        "content_type": content_type,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def builtin_web_tools(brave_api_key: str | None = None) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="web_search",
            description="Search the web for up-to-date information.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_web_search_factory(brave_api_key),
        ),
        ToolDefinition(
            name="web_fetch",
            description="Fetch URL content and return text.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer"},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_web_fetch,
        ),
    ]
