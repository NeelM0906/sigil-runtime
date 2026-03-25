"""SEO research tools powered by KeywordsPeopleUse API."""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

log = logging.getLogger(__name__)

_BASE_URL = "https://keywordspeopleuse.com/api"


def _api_key() -> str:
    key = os.getenv("KEYWORDSPEOPLEUSE_API_KEY", "")
    if not key:
        raise ValueError("KEYWORDSPEOPLEUSE_API_KEY not set")
    return key


def _get(path: str, params: dict[str, str]) -> dict[str, Any]:
    """Make an authenticated GET request to the KeywordsPeopleUse API."""
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    url = f"{_BASE_URL}/{path}?{query}"
    req = urllib.request.Request(url, headers={
        "x-api-key": _api_key(),
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """Make an authenticated POST request."""
    url = f"{_BASE_URL}/{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "x-api-key": _api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Tool implementations ─────────────────────────────────────────────


def _seo_people_also_ask(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Get Google 'People Also Ask' questions for a keyword."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("alsoask", {
        "q": q,
        "gl": str(arguments.get("location") or arguments.get("gl") or "us"),
        "hl": str(arguments.get("language") or arguments.get("hl") or "en"),
    })


def _seo_autocomplete(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Get Google autocomplete suggestions for a keyword."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("suggestions", {
        "q": q,
        "gl": str(arguments.get("location") or "us"),
        "hl": str(arguments.get("language") or "en"),
    })


def _seo_reddit_quora(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Get questions from Reddit and Quora for a keyword."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("forums", {
        "q": q,
        "gl": str(arguments.get("location") or "us"),
        "hl": str(arguments.get("language") or "en"),
    })


def _seo_keyword_clusters(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Generate keyword clusters organized by search intent."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("clustering", {
        "q": q,
        "gl": str(arguments.get("location") or "us"),
        "hl": str(arguments.get("language") or "en"),
    })


def _seo_content_explorer(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Explore top-ranking content for a keyword."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("content", {
        "q": q,
        "gl": str(arguments.get("location") or "us"),
        "hl": str(arguments.get("language") or "en"),
    })


def _seo_ai_assistant(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Use the SEO AI assistant for content generation tasks."""
    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt is required")
    body: dict[str, Any] = {"prompt": prompt}
    command = arguments.get("command")
    if command and str(command).strip():
        body["command"] = str(command).strip()
    hl = arguments.get("language")
    if hl:
        body["hl"] = str(hl)
    return _post("completions", body)


def _seo_semantic_keywords(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Get semantically related keywords."""
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    return _get("semantic_keywords", {
        "q": q,
        "gl": str(arguments.get("location") or "us"),
        "hl": str(arguments.get("language") or "en"),
    })


def _seo_full_research(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Run a complete SEO research pipeline for a keyword.

    Calls People Also Ask + Reddit/Quora + Keyword Clusters +
    Semantic Keywords + Autocomplete and returns a consolidated report.
    """
    q = str(arguments.get("keyword") or arguments.get("q") or "").strip()
    if not q:
        raise ValueError("keyword is required")
    gl = str(arguments.get("location") or "us")
    hl = str(arguments.get("language") or "en")
    params = {"q": q, "gl": gl, "hl": hl}

    results = {}
    for name, path in [
        ("people_also_ask", "alsoask"),
        ("reddit_quora", "forums"),
        ("keyword_clusters", "clustering"),
        ("semantic_keywords", "semantic_keywords"),
        ("autocomplete", "suggestions"),
    ]:
        try:
            results[name] = _get(path, params)
        except Exception as exc:
            results[name] = {"error": str(exc)}

    return {
        "keyword": q,
        "location": gl,
        "language": hl,
        "results": results,
    }


# ── Tool definitions ─────────────────────────────────────────────────

_KEYWORD_PARAMS = {
    "type": "object",
    "properties": {
        "keyword": {"type": "string", "description": "The keyword or phrase to research"},
        "location": {"type": "string", "description": "Country code (us, uk, fr, etc). Default: us"},
        "language": {"type": "string", "description": "Language code (en, es, fr, de, etc). Default: en"},
    },
    "required": ["keyword"],
    "additionalProperties": False,
}


def builtin_seo_tools() -> list[ToolDefinition]:
    """Return SEO research tools powered by KeywordsPeopleUse API."""
    if not os.getenv("KEYWORDSPEOPLEUSE_API_KEY"):
        return []

    return [
        ToolDefinition(
            name="seo_people_also_ask",
            description="Get Google 'People Also Ask' questions for a keyword. Returns real questions real humans type into Google. Use for content ideas, FAQ sections, video hooks, and landing page headlines.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_people_also_ask,
        ),
        ToolDefinition(
            name="seo_autocomplete",
            description="Get Google autocomplete suggestions showing what people search for. Use for long-tail keyword discovery and understanding search behavior.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_autocomplete,
        ),
        ToolDefinition(
            name="seo_reddit_quora",
            description="Mine Reddit and Quora for raw, unfiltered questions and pain points about a topic. Returns real forum discussions revealing what people struggle with.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_reddit_quora,
        ),
        ToolDefinition(
            name="seo_keyword_clusters",
            description="Generate keyword clusters organized by search intent (who/what/how/why). Use for content planning, silo structure, and topical authority mapping.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_keyword_clusters,
        ),
        ToolDefinition(
            name="seo_content_explorer",
            description="Explore top-ranking content for a keyword. See what's already ranking, content gaps, and opportunities.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_content_explorer,
        ),
        ToolDefinition(
            name="seo_semantic_keywords",
            description="Get semantically related keywords and LSI terms. Use for enriching content with topically relevant language.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_semantic_keywords,
        ),
        ToolDefinition(
            name="seo_ai_assistant",
            description="SEO AI assistant for content generation. Commands: seo_article_with_faq, topical_map, content_brief, silo_structure. Or pass a custom prompt.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The SEO task or question"},
                    "command": {
                        "type": "string",
                        "description": "Optional template: seo_article_with_faq, topical_map, content_brief, silo_structure",
                        "enum": ["seo_article_with_faq", "topical_map", "content_brief", "silo_structure"],
                    },
                    "language": {"type": "string", "description": "Language code for output"},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_seo_ai_assistant,
        ),
        ToolDefinition(
            name="seo_full_research",
            description="Run a complete SEO research pipeline: People Also Ask + Reddit/Quora + Keyword Clusters + Semantic Keywords + Autocomplete. Returns a consolidated report for a single keyword. Use when you need comprehensive keyword intelligence.",
            parameters=_KEYWORD_PARAMS,
            risk_level="low",
            action_type="read",
            execute=_seo_full_research,
        ),
    ]
