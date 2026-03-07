"""Tests for Pinecone tenant/being scoping.

Verifies that:
- pinecone_upsert injects tenant_id and being_id into vector metadata
- pinecone_query adds a tenant_id filter to the Pinecone request
- pinecone_multi_query adds a tenant_id filter to each sub-query
- Extra metadata from the caller is preserved alongside scoping fields
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.tools.builtin_pinecone import (
    _pinecone_multi_query_factory,
    _pinecone_query_factory,
    _pinecone_upsert_factory,
)


@dataclass
class _FakeContext:
    """Minimal stand-in for ToolContext used in pinecone tool tests."""
    tenant_id: str = "tenant-acme"
    session_id: str = "sister:scholar:sess-1"
    turn_id: str = "turn-1"
    user_id: str = "user-local"
    workspace_root: Path = field(default_factory=lambda: Path("/tmp/fake"))
    db: Any = None
    guard_path: Any = None
    loop_state_ref: Any = None


# ---------------------------------------------------------------------------
# Upsert scoping
# ---------------------------------------------------------------------------

class TestUpsertTenantScoping:
    """pinecone_upsert must inject tenant_id and being_id into metadata."""

    def _run_upsert(self, context, extra_metadata=None):
        """Run the upsert factory with mocked HTTP + embeddings."""
        run = _pinecone_upsert_factory(default_index="test-idx", default_namespace="ns1")
        args: dict[str, Any] = {"texts": ["hello world"]}
        if extra_metadata is not None:
            args["metadata"] = extra_metadata

        captured_payloads: list[dict] = []

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            captured_payloads.append({"method": method, "url": url, "payload": payload})
            if "upsert" in url:
                return {"upsertedCount": 1}
            return {}

        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_batch", return_value=[[0.1, 0.2, 0.3]]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="fake-key"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="host.pinecone.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run(args, context)
        return result, captured_payloads

    def test_tenant_id_injected(self):
        ctx = _FakeContext(tenant_id="tenant-acme")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["tenant_id"] == "tenant-acme"

    def test_being_id_injected_via_session(self):
        ctx = _FakeContext(session_id="mc-chat-scholar")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["being_id"] == "scholar"

    def test_being_id_injected_via_subtask(self):
        ctx = _FakeContext(session_id="subtask:task-123:forge")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["being_id"] == "forge"

    def test_being_id_injected_via_user_id(self):
        ctx = _FakeContext(session_id="plain-session", user_id="prime->analyst")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["being_id"] == "analyst"

    def test_being_id_none_when_unresolvable(self):
        ctx = _FakeContext(session_id="plain-session", user_id="user-local")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["being_id"] is None
        assert vec_meta["tenant_id"] == "tenant-acme"

    def test_extra_metadata_preserved(self):
        ctx = _FakeContext()
        _, payloads = self._run_upsert(ctx, extra_metadata={"source": "docs", "page": 3})
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["source"] == "docs"
        assert vec_meta["page"] == 3
        assert vec_meta["tenant_id"] == "tenant-acme"

    def test_text_field_present(self):
        ctx = _FakeContext()
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["text"] == "hello world"

    def test_empty_tenant_id_stored_as_none(self):
        ctx = _FakeContext(tenant_id="")
        _, payloads = self._run_upsert(ctx)
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["tenant_id"] is None

    def test_extra_metadata_overrides_scoping(self):
        """Caller can intentionally override tenant_id via extra_metadata."""
        ctx = _FakeContext(tenant_id="tenant-acme")
        _, payloads = self._run_upsert(ctx, extra_metadata={"tenant_id": "tenant-custom"})
        upsert_call = [p for p in payloads if "upsert" in p["url"]][0]
        vec_meta = upsert_call["payload"]["vectors"][0]["metadata"]
        assert vec_meta["tenant_id"] == "tenant-custom"


# ---------------------------------------------------------------------------
# Query scoping
# ---------------------------------------------------------------------------

class TestQueryTenantScoping:
    """pinecone_query must add a tenant_id filter to the Pinecone request."""

    def _run_query(self, context, query="test query", extra_args=None, match_response=None):
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        captured_payloads: list[dict] = []
        default_resp = match_response or {"matches": [{"id": "v1", "score": 0.9, "metadata": {"text": "hit"}}]}

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            captured_payloads.append({"method": method, "url": url, "payload": payload})
            return default_resp

        args = {"query": query}
        if extra_args:
            args.update(extra_args)

        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1, 0.2, 0.3]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="fake-key"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="host.pinecone.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run(args, context)
        return result, captured_payloads

    def test_tenant_filter_added(self):
        ctx = _FakeContext(tenant_id="tenant-acme")
        _, payloads = self._run_query(ctx)
        query_payload = payloads[0]["payload"]
        assert query_payload["filter"] == {"tenant_id": {"$eq": "tenant-acme"}}

    def test_no_filter_when_tenant_empty(self):
        ctx = _FakeContext(tenant_id="")
        _, payloads = self._run_query(ctx)
        query_payload = payloads[0]["payload"]
        assert "filter" not in query_payload

    def test_caller_filter_merged_with_tenant(self):
        """Caller-supplied filter is merged via $and with tenant scoping."""
        ctx = _FakeContext(tenant_id="tenant-acme")
        caller_filter = {"source": {"$eq": "docs"}}
        _, payloads = self._run_query(ctx, extra_args={"filter": caller_filter})
        query_payload = payloads[0]["payload"]
        assert query_payload["filter"] == {
            "$and": [
                {"tenant_id": {"$eq": "tenant-acme"}},
                {"source": {"$eq": "docs"}},
            ]
        }

    def test_caller_filter_alone_when_no_tenant(self):
        """Without tenant, caller filter is used as-is."""
        ctx = _FakeContext(tenant_id="")
        caller_filter = {"source": {"$eq": "docs"}}
        _, payloads = self._run_query(ctx, extra_args={"filter": caller_filter})
        query_payload = payloads[0]["payload"]
        assert query_payload["filter"] == {"source": {"$eq": "docs"}}

    def test_no_being_id_filter(self):
        """Query must NOT filter by being_id — beings read all tenant vectors."""
        ctx = _FakeContext(tenant_id="tenant-acme", session_id="mc-chat-scholar")
        _, payloads = self._run_query(ctx)
        query_payload = payloads[0]["payload"]
        filt = query_payload["filter"]
        assert "being_id" not in json.dumps(filt)

    def test_query_still_returns_results(self):
        ctx = _FakeContext()
        result, _ = self._run_query(ctx)
        assert "results" in result
        assert result["query"] == "test query"


# ---------------------------------------------------------------------------
# Multi-query scoping
# ---------------------------------------------------------------------------

class TestMultiQueryTenantScoping:
    """pinecone_multi_query must add tenant_id filter to each sub-query."""

    def _run_multi_query(self, context, indexes=None, match_response=None):
        run = _pinecone_multi_query_factory(default_namespace="ns1")
        captured_payloads: list[dict] = []
        default_resp = match_response or {"matches": [{"id": "v1", "score": 0.9, "metadata": {"text": "hit"}}]}

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            captured_payloads.append({"method": method, "url": url, "payload": payload})
            return default_resp

        if indexes is None:
            indexes = [{"index_name": "idx-a"}, {"index_name": "idx-b"}]

        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1, 0.2, 0.3]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="fake-key"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="host.pinecone.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run(
                {"query": "multi test", "indexes": indexes},
                context,
            )
        return result, captured_payloads

    def test_tenant_filter_on_each_sub_query(self):
        ctx = _FakeContext(tenant_id="tenant-acme")
        _, payloads = self._run_multi_query(ctx)
        query_calls = [p for p in payloads if "/query" in p["url"]]
        # With results returned, no fallback — exactly 2 calls
        assert len(query_calls) == 2
        for call in query_calls:
            assert call["payload"]["filter"] == {"tenant_id": {"$eq": "tenant-acme"}}

    def test_no_filter_when_tenant_empty(self):
        ctx = _FakeContext(tenant_id="")
        _, payloads = self._run_multi_query(ctx)
        query_calls = [p for p in payloads if "/query" in p["url"]]
        for call in query_calls:
            assert "filter" not in call["payload"]

    def test_per_index_filter_merged_with_tenant(self):
        """Per-index caller filter merged with tenant via $and."""
        ctx = _FakeContext(tenant_id="tenant-acme")
        indexes = [
            {"index_name": "idx-a", "filter": {"category": {"$eq": "finance"}}},
        ]
        _, payloads = self._run_multi_query(ctx, indexes=indexes)
        query_calls = [p for p in payloads if "/query" in p["url"]]
        assert len(query_calls) == 1
        assert query_calls[0]["payload"]["filter"] == {
            "$and": [
                {"tenant_id": {"$eq": "tenant-acme"}},
                {"category": {"$eq": "finance"}},
            ]
        }


# ---------------------------------------------------------------------------
# Legacy fallback
# ---------------------------------------------------------------------------

class TestLegacyFallback:
    """When scoped query returns 0 results, retry without tenant filter."""

    def test_query_fallback_on_empty_scoped_results(self):
        """Scoped query returns nothing -> fallback unscoped query fires."""
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        call_count = [0]

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (scoped) returns empty
                return {"matches": []}
            # Second call (unscoped fallback) returns legacy data
            return {"matches": [{"id": "legacy-1", "score": 0.95, "metadata": {"text": "old data"}}]}

        ctx = _FakeContext(tenant_id="tenant-acme")
        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1, 0.2]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="k"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="h.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run({"query": "test"}, ctx)

        assert call_count[0] == 2
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "legacy-1"
        assert result["legacy_fallback"] is True

    def test_query_no_fallback_when_scoped_has_results(self):
        """If scoped query returns results, no fallback is triggered."""
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        call_count = [0]

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            call_count[0] += 1
            return {"matches": [{"id": "scoped-1", "score": 0.9, "metadata": {"text": "scoped"}}]}

        ctx = _FakeContext(tenant_id="tenant-acme")
        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1, 0.2]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="k"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="h.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run({"query": "test"}, ctx)

        assert call_count[0] == 1
        assert "legacy_fallback" not in result
        assert len(result["results"]) == 1

    def test_query_no_fallback_when_no_tenant(self):
        """Without tenant scoping, no fallback needed."""
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        call_count = [0]

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            call_count[0] += 1
            return {"matches": []}

        ctx = _FakeContext(tenant_id="")
        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1, 0.2]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="k"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="h.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            result = run({"query": "test"}, ctx)

        assert call_count[0] == 1
        assert "legacy_fallback" not in result

    def test_fallback_logs_warning(self):
        """Fallback emits a warning log about legacy unscoped vectors."""
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        call_count = [0]

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"matches": []}
            return {"matches": [{"id": "v1", "score": 0.9, "metadata": {"text": "x"}}]}

        ctx = _FakeContext(tenant_id="tenant-acme")
        import logging
        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="k"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="h.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
            patch("bomba_sr.tools.builtin_pinecone.log") as mock_log,
        ):
            run({"query": "test"}, ctx)

        mock_log.warning.assert_called_once()
        warning_msg = mock_log.warning.call_args[0][0]
        assert "Legacy unscoped vectors" in warning_msg
        assert "re-indexing" in warning_msg

    def test_fallback_preserves_caller_filter(self):
        """Fallback drops tenant filter but keeps caller filter."""
        run = _pinecone_query_factory(default_index="test-idx", default_namespace="ns1")
        captured_payloads: list[dict] = []
        call_count = [0]

        def fake_http(method, url, *, headers=None, payload=None, timeout=30):
            captured_payloads.append({"method": method, "url": url, "payload": payload})
            call_count[0] += 1
            if call_count[0] == 1:
                return {"matches": []}
            return {"matches": [{"id": "v1", "score": 0.9, "metadata": {"text": "x"}}]}

        ctx = _FakeContext(tenant_id="tenant-acme")
        with (
            patch("bomba_sr.tools.builtin_pinecone._embed_query", return_value=[0.1]),
            patch("bomba_sr.tools.builtin_pinecone._choose_pinecone_api_key", return_value="k"),
            patch("bomba_sr.tools.builtin_pinecone._resolve_index_host", return_value="h.io"),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            run({"query": "test", "filter": {"source": {"$eq": "docs"}}}, ctx)

        # First call: $and with tenant + caller
        assert "$and" in json.dumps(captured_payloads[0]["payload"].get("filter", {}))
        # Fallback call: only caller filter, no tenant
        fallback_filter = captured_payloads[1]["payload"].get("filter")
        assert fallback_filter == {"source": {"$eq": "docs"}}
