"""Live integration tests for SEO tools (KeywordsPeopleUse API).

These tests hit the real API. They require KEYWORDSPEOPLEUSE_API_KEY in env.
Skipped automatically if the key is not set.
"""
from __future__ import annotations

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("KEYWORDSPEOPLEUSE_API_KEY"),
    reason="KEYWORDSPEOPLEUSE_API_KEY not set — skipping live SEO tests",
)


@pytest.fixture
def seo():
    """Import the module with the key guaranteed present."""
    import bomba_sr.tools.builtin_seo as mod
    return mod


class TestSeoToolsLive:
    """Live API tests — each hits one endpoint with a real query."""

    def test_people_also_ask(self, seo):
        # alsoask endpoint can take 60s+ for uncached queries
        try:
            result = seo._get("alsoask", {"q": "SEO", "gl": "us", "hl": "en"})
            assert "result" in result
            res = result["result"]
            assert "question" in res
        except (TimeoutError, OSError) as exc:
            pytest.skip(f"alsoask endpoint timed out (known slow): {exc}")

    def test_autocomplete(self, seo):
        result = seo._get("suggestions", {"q": "no surprise act", "gl": "us", "hl": "en"})
        assert "result" in result
        res = result["result"]
        assert "question" in res
        # Autocomplete returns children with suggestion words
        assert "children" in res

    def test_reddit_quora(self, seo):
        result = seo._get("forums", {"q": "insurance claim denied", "gl": "us", "hl": "en"})
        assert "result" in result

    def test_keyword_clusters(self, seo):
        result = seo._get("clustering", {"q": "healthcare revenue cycle", "gl": "us", "hl": "en"})
        assert "result" in result

    def test_semantic_keywords(self, seo):
        result = seo._get("semantic_keywords", {"q": "balance billing", "gl": "us", "hl": "en"})
        assert "result" in result

    def test_content_explorer(self, seo):
        result = seo._get("content", {"q": "out of network reimbursement", "gl": "us", "hl": "en"})
        assert "result" in result

    def test_ai_assistant(self, seo):
        result = seo._post("completions", {
            "prompt": "Write 3 FAQ questions about medical billing disputes",
        })
        # The AI endpoint returns a completion
        assert result is not None
        # Should have some text response
        assert any(k in result for k in ("result", "text", "completion", "choices", "output"))

    def test_full_research_pipeline(self, seo):
        """Test the consolidated pipeline tool function."""
        from unittest.mock import MagicMock
        ctx = MagicMock()
        result = seo._seo_full_research({"keyword": "PPO contract rates"}, ctx)

        assert result["keyword"] == "PPO contract rates"
        assert result["location"] == "us"
        assert "results" in result

        # Should have attempted all 5 sub-queries
        sections = result["results"]
        assert "people_also_ask" in sections
        assert "reddit_quora" in sections
        assert "keyword_clusters" in sections
        assert "semantic_keywords" in sections
        assert "autocomplete" in sections

        # At least some should have succeeded (not all errors)
        successes = sum(1 for v in sections.values() if "error" not in v)
        assert successes >= 3, f"Only {successes}/5 sub-queries succeeded: {sections}"


class TestSeoToolRegistration:
    """Verify tool registration behavior."""

    def test_tools_registered_with_key(self, seo):
        tools = seo.builtin_seo_tools()
        assert len(tools) == 8
        names = {t.name for t in tools}
        assert "seo_people_also_ask" in names
        assert "seo_full_research" in names
        assert "seo_ai_assistant" in names

    def test_all_tools_are_read_only(self, seo):
        tools = seo.builtin_seo_tools()
        for t in tools:
            assert t.action_type == "read", f"{t.name} should be read-only"
            assert t.risk_level == "low", f"{t.name} should be low risk"

    def test_no_tools_without_key(self):
        """Without API key, no tools should be registered."""
        old = os.environ.pop("KEYWORDSPEOPLEUSE_API_KEY", None)
        try:
            from bomba_sr.tools.builtin_seo import builtin_seo_tools
            tools = builtin_seo_tools()
            assert len(tools) == 0
        finally:
            if old:
                os.environ["KEYWORDSPEOPLEUSE_API_KEY"] = old
