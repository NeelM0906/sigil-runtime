"""Browser tools — headless Chromium via Playwright.

Provides tools for opening web pages, taking screenshots, clicking,
typing, and extracting content from JS-rendered sites.

Each call spins up its own Playwright + Chromium context to avoid
greenlet threading issues when called from ThreadPoolExecutor workers.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

log = logging.getLogger(__name__)

_SCREENSHOT_DIR = Path(os.getenv("BOMBA_WORKSPACE", ".")) / "projects" / "screenshots"


def _run_in_browser(fn):
    """Run a function with a fresh Playwright browser, thread-safe."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            return fn(browser)
        finally:
            browser.close()


def _browser_open(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Open a URL in headless browser, return rendered text + optional screenshot."""
    url = str(arguments.get("url") or "").strip()
    if not url:
        return {"error": "url is required"}
    take_screenshot = bool(arguments.get("screenshot", False))
    wait_ms = min(int(arguments.get("wait_ms") or 3000), 15000)
    max_chars = int(arguments.get("max_chars") or 15000)

    def _do(browser):
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)

            title = page.title()
            text = page.inner_text("body")[:max_chars]

            result: dict[str, Any] = {
                "url": page.url,
                "title": title,
                "text": text,
            }

            if take_screenshot:
                _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
                fname = f"screenshot_{hash(url) % 100000:05d}.png"
                path = _SCREENSHOT_DIR / fname
                page.screenshot(path=str(path), full_page=False)
                result["screenshot_path"] = str(path)

            return result
        finally:
            page.close()

    try:
        return _run_in_browser(_do)
    except Exception as exc:
        return {"error": str(exc)[:500]}


def _browser_screenshot(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Take a screenshot of a URL and save it."""
    url = str(arguments.get("url") or "").strip()
    if not url:
        return {"error": "url is required"}
    full_page = bool(arguments.get("full_page", False))
    wait_ms = min(int(arguments.get("wait_ms") or 3000), 15000)

    def _do(browser):
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)

            _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"screenshot_{hash(url) % 100000:05d}.png"
            path = _SCREENSHOT_DIR / fname
            page.screenshot(path=str(path), full_page=full_page)

            return {
                "url": page.url,
                "title": page.title(),
                "screenshot_path": str(path),
            }
        finally:
            page.close()

    try:
        return _run_in_browser(_do)
    except Exception as exc:
        return {"error": str(exc)[:500]}


def _browser_click(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Open a page, click a selector, return the resulting page text."""
    url = str(arguments.get("url") or "").strip()
    selector = str(arguments.get("selector") or "").strip()
    if not url or not selector:
        return {"error": "url and selector are required"}
    wait_ms = min(int(arguments.get("wait_ms") or 2000), 15000)
    max_chars = int(arguments.get("max_chars") or 15000)

    def _do(browser):
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            page.click(selector, timeout=10000)
            page.wait_for_timeout(wait_ms)

            return {
                "url": page.url,
                "title": page.title(),
                "text": page.inner_text("body")[:max_chars],
            }
        finally:
            page.close()

    try:
        return _run_in_browser(_do)
    except Exception as exc:
        return {"error": str(exc)[:500]}


def _browser_fill(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Open a page, fill a form field, optionally submit."""
    url = str(arguments.get("url") or "").strip()
    selector = str(arguments.get("selector") or "").strip()
    value = str(arguments.get("value") or "")
    submit = bool(arguments.get("submit", False))
    if not url or not selector:
        return {"error": "url and selector are required"}
    max_chars = int(arguments.get("max_chars") or 15000)

    def _do(browser):
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            page.fill(selector, value, timeout=10000)
            if submit:
                page.press(selector, "Enter")
                page.wait_for_timeout(3000)

            return {
                "url": page.url,
                "title": page.title(),
                "text": page.inner_text("body")[:max_chars],
            }
        finally:
            page.close()

    try:
        return _run_in_browser(_do)
    except Exception as exc:
        return {"error": str(exc)[:500]}


def _browser_extract(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Open a page and extract content from specific selectors."""
    url = str(arguments.get("url") or "").strip()
    selectors = arguments.get("selectors") or []
    if not url:
        return {"error": "url is required"}
    if not selectors:
        selectors = ["body"]
    wait_ms = min(int(arguments.get("wait_ms") or 3000), 15000)

    def _do(browser):
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)

            extracted: dict[str, str] = {}
            for sel in selectors[:10]:
                try:
                    el = page.query_selector(str(sel))
                    extracted[sel] = el.inner_text()[:5000] if el else "[not found]"
                except Exception:
                    extracted[sel] = "[error]"

            return {
                "url": page.url,
                "title": page.title(),
                "extracted": extracted,
            }
        finally:
            page.close()

    try:
        return _run_in_browser(_do)
    except Exception as exc:
        return {"error": str(exc)[:500]}


def builtin_browser_tools() -> list[ToolDefinition]:
    """Return browser tool definitions."""
    return [
        ToolDefinition(
            name="browser_open",
            description=(
                "Open a URL in a headless browser (renders JavaScript). "
                "Returns the page title and rendered text content. "
                "Optionally takes a screenshot."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"},
                    "screenshot": {"type": "boolean", "description": "Take a screenshot", "default": False},
                    "wait_ms": {"type": "integer", "description": "Wait time after load (ms)", "default": 3000},
                    "max_chars": {"type": "integer", "description": "Max text chars to return", "default": 15000},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_browser_open,
        ),
        ToolDefinition(
            name="browser_screenshot",
            description="Take a screenshot of a web page. Returns the file path to the saved PNG.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to screenshot"},
                    "full_page": {"type": "boolean", "description": "Capture full page", "default": False},
                    "wait_ms": {"type": "integer", "description": "Wait time after load (ms)", "default": 3000},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_browser_screenshot,
        ),
        ToolDefinition(
            name="browser_click",
            description="Open a page and click an element by CSS selector. Returns the resulting page text.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"},
                    "selector": {"type": "string", "description": "CSS selector to click"},
                    "wait_ms": {"type": "integer", "description": "Wait after click (ms)", "default": 2000},
                    "max_chars": {"type": "integer", "description": "Max text chars", "default": 15000},
                },
                "required": ["url", "selector"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="write",
            execute=_browser_click,
        ),
        ToolDefinition(
            name="browser_fill",
            description="Open a page, fill a form field, optionally press Enter to submit.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"},
                    "selector": {"type": "string", "description": "CSS selector of the input field"},
                    "value": {"type": "string", "description": "Text to type into the field"},
                    "submit": {"type": "boolean", "description": "Press Enter after filling", "default": False},
                    "max_chars": {"type": "integer", "description": "Max text chars", "default": 15000},
                },
                "required": ["url", "selector", "value"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="write",
            execute=_browser_fill,
        ),
        ToolDefinition(
            name="browser_extract",
            description="Open a page and extract text content from specific CSS selectors.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"},
                    "selectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "CSS selectors to extract text from",
                    },
                    "wait_ms": {"type": "integer", "description": "Wait time after load (ms)", "default": 3000},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="read",
            execute=_browser_extract,
        ),
    ]
