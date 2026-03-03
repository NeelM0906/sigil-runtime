from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools import builtin_pinecone as pinecone_mod
from bomba_sr.tools.builtin_pinecone import builtin_pinecone_tools


def _context() -> ToolContext:
    return ToolContext(
        tenant_id="tenant",
        session_id="session",
        turn_id="turn",
        user_id="user",
        workspace_root=Path.cwd(),
        db=RuntimeDB(":memory:"),
        guard_path=lambda p: Path(p),
    )


class PineconeToolTests(unittest.TestCase):
    def test_query_filters_by_score(self) -> None:
        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "ublib2", "host": "idx-host"}]}
            if "openai.com/v1/embeddings" in url:
                return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
            if "idx-host/query" in url:
                return {
                    "matches": [
                        {"id": "m1", "score": 0.91, "metadata": {"text": "hit-1"}},
                        {"id": "m2", "score": 0.25, "metadata": {"text": "hit-2"}},
                    ]
                }
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {
                    "PINECONE_API_KEY": "pc-key",
                    "OPENAI_API_KEY": "oa-key",
                },
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            result = query_tool.execute({"query": "hello world", "score_threshold": 0.4}, _context())
            self.assertEqual(result["index_name"], "ublib2")
            self.assertEqual(len(result["results"]), 1)
            self.assertEqual(result["results"][0]["id"], "m1")

    def test_list_indexes_with_vector_counts(self) -> None:
        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "ublib2", "host": "idx-host", "metric": "cosine"}]}
            if "idx-host/describe_index_stats" in url:
                return {"totalVectorCount": 1234}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict("os.environ", {"PINECONE_API_KEY": "pc-key-many"}, clear=False),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            list_tool = next(t for t in tools if t.name == "pinecone_list_indexes")
            result = list_tool.execute({}, _context())
            self.assertEqual(len(result["indexes"]), 1)
            self.assertEqual(result["indexes"][0]["name"], "ublib2")
            self.assertEqual(result["indexes"][0]["vector_count"], 1234)

    def test_strata_index_uses_strata_key(self) -> None:
        seen_keys: list[str] = []

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if headers and "Api-Key" in headers:
                seen_keys.append(str(headers["Api-Key"]))
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "oracleinfluencemastery", "host": "strata-host"}]}
            if "openai.com/v1/embeddings" in url:
                return {"data": [{"embedding": [0.1, 0.2]}]}
            if "strata-host/query" in url:
                return {"matches": []}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {
                    "PINECONE_API_KEY": "default-key",
                    "PINECONE_API_KEY_STRATA": "strata-key",
                    "OPENAI_API_KEY": "oa-key",
                },
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            query_tool.execute({"query": "x", "index_name": "oracleinfluencemastery"}, _context())
            self.assertIn("strata-key", seen_keys)

    def test_athena_uses_primary_key(self) -> None:
        """athenacontextualmemory belongs to primary account, not STRATA."""
        seen_keys: list[str] = []

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if headers and "Api-Key" in headers:
                seen_keys.append(str(headers["Api-Key"]))
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "athenacontextualmemory", "host": "athena-host"}]}
            if "openai.com/v1/embeddings" in url:
                return {"data": [{"embedding": [0.1, 0.2]}]}
            if "athena-host/query" in url:
                return {"matches": []}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {
                    "PINECONE_API_KEY": "primary-key",
                    "PINECONE_API_KEY_STRATA": "strata-key",
                    "OPENAI_API_KEY": "oa-key",
                },
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            query_tool.execute({"query": "x", "index_name": "athenacontextualmemory"}, _context())
            # Must use primary key, NOT strata key
            self.assertIn("primary-key", seen_keys)
            self.assertNotIn("strata-key", seen_keys)

    def test_missing_key_raises(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PINECONE_API_KEY": "",
                "PINECONE_API_KEY_STRATA": "",
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            with self.assertRaises(ValueError):
                query_tool.execute({"query": "hello"}, _context())

    def test_rejects_unsafe_index_name(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PINECONE_API_KEY": "pc-key",
                "OPENAI_API_KEY": "oa-key",
            },
            clear=False,
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            with self.assertRaises(ValueError):
                query_tool.execute({"query": "hello", "index_name": "../admin/keys"}, _context())

    def test_embedding_model_reads_env_override(self) -> None:
        seen_models: list[str] = []

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "ublib2", "host": "idx-host"}]}
            if "openai.com/v1/embeddings" in url:
                if isinstance(payload, dict):
                    seen_models.append(str(payload.get("model")))
                return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
            if "idx-host/query" in url:
                return {"matches": []}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {
                    "PINECONE_API_KEY": "pc-key",
                    "OPENAI_API_KEY": "oa-key",
                    "BOMBA_PINECONE_EMBED_MODEL": "text-embedding-3-large",
                },
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            query_tool = next(t for t in tools if t.name == "pinecone_query")
            query_tool.execute({"query": "hello world"}, _context())
            self.assertIn("text-embedding-3-large", seen_models)

    def test_list_indexes_caps_describe_calls(self) -> None:
        describe_calls = 0
        with pinecone_mod._INDEX_CACHE_LOCK:
            pinecone_mod._INDEX_CACHE.clear()

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            nonlocal describe_calls
            if "api.pinecone.io/indexes" in url:
                return {
                    "indexes": [
                        {"name": f"idx-{i}", "host": f"idx-{i}.example.test", "metric": "cosine"}
                        for i in range(8)
                    ]
                }
            if "/describe_index_stats" in url:
                describe_calls += 1
                return {"totalVectorCount": 10}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict("os.environ", {"PINECONE_API_KEY": "pc-key"}, clear=False),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            list_tool = next(t for t in tools if t.name == "pinecone_list_indexes")
            result = list_tool.execute({}, _context())
            self.assertEqual(len(result["indexes"]), 8)
            self.assertEqual(describe_calls, 5)

    def test_upsert_sends_vectors(self) -> None:
        upsert_payloads: list[dict] = []

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if "api.pinecone.io/indexes" in url:
                return {"indexes": [{"name": "ublib2", "host": "idx-host"}]}
            if "openai.com/v1/embeddings" in url:
                texts = payload.get("input", []) if isinstance(payload, dict) else []
                return {
                    "data": [
                        {"index": i, "embedding": [0.1 * (i + 1), 0.2 * (i + 1)]}
                        for i in range(len(texts))
                    ]
                }
            if "idx-host/vectors/upsert" in url:
                upsert_payloads.append(payload)
                return {"upsertedCount": len(payload.get("vectors", []))}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {"PINECONE_API_KEY": "pc-key", "OPENAI_API_KEY": "oa-key"},
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            upsert_tool = next(t for t in tools if t.name == "pinecone_upsert")
            result = upsert_tool.execute(
                {"texts": ["chunk one", "chunk two"], "metadata": {"source": "test"}},
                _context(),
            )
            self.assertEqual(result["upserted_count"], 2)
            self.assertEqual(result["index_name"], "ublib2")
            self.assertEqual(result["namespace"], "longterm")
            # Verify payload structure
            self.assertEqual(len(upsert_payloads), 1)
            vectors = upsert_payloads[0]["vectors"]
            self.assertEqual(len(vectors), 2)
            self.assertIn("text", vectors[0]["metadata"])
            self.assertEqual(vectors[0]["metadata"]["source"], "test")
            self.assertEqual(upsert_payloads[0]["namespace"], "longterm")

    def test_upsert_validates_index_name(self) -> None:
        with patch.dict(
            "os.environ",
            {"PINECONE_API_KEY": "pc-key", "OPENAI_API_KEY": "oa-key"},
            clear=False,
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            upsert_tool = next(t for t in tools if t.name == "pinecone_upsert")
            with self.assertRaises(ValueError):
                upsert_tool.execute(
                    {"texts": ["hello"], "index_name": "../evil/path"},
                    _context(),
                )

    def test_multi_query_merges_results(self) -> None:
        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            if "api.pinecone.io/indexes" in url:
                return {
                    "indexes": [
                        {"name": "idx-a", "host": "host-a"},
                        {"name": "idx-b", "host": "host-b"},
                    ]
                }
            if "openai.com/v1/embeddings" in url:
                return {"data": [{"embedding": [0.1, 0.2]}]}
            if "host-a/query" in url:
                return {
                    "matches": [
                        {"id": "a1", "score": 0.95, "metadata": {"text": "top hit"}},
                        {"id": "a2", "score": 0.70, "metadata": {"text": "mid hit"}},
                    ]
                }
            if "host-b/query" in url:
                return {
                    "matches": [
                        {"id": "b1", "score": 0.85, "metadata": {"text": "second hit"}},
                        {"id": "b2", "score": 0.60, "metadata": {"text": "top hit"}},  # duplicate text
                    ]
                }
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {"PINECONE_API_KEY": "pc-key", "OPENAI_API_KEY": "oa-key"},
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            mq_tool = next(t for t in tools if t.name == "pinecone_multi_query")
            result = mq_tool.execute(
                {
                    "query": "test",
                    "indexes": [
                        {"index_name": "idx-a"},
                        {"index_name": "idx-b"},
                    ],
                },
                _context(),
            )
            self.assertEqual(len(result["indexes_queried"]), 2)
            # Sorted by score desc, deduplicated by text
            results = result["results"]
            # "top hit" at 0.95 from idx-a, "second hit" at 0.85 from idx-b, "mid hit" at 0.70 from idx-a
            # "top hit" at 0.60 from idx-b is a duplicate and should be removed
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["score"], 0.95)
            self.assertEqual(results[0]["source_index"], "idx-a")
            # All results have source_index annotation
            for r in results:
                self.assertIn("source_index", r)

    def test_multi_query_embeds_once(self) -> None:
        embed_calls = 0

        def fake_http(method, url, headers=None, payload=None, timeout=30):  # noqa: ANN001
            nonlocal embed_calls
            if "api.pinecone.io/indexes" in url:
                return {
                    "indexes": [
                        {"name": "idx-a", "host": "host-a"},
                        {"name": "idx-b", "host": "host-b"},
                    ]
                }
            if "openai.com/v1/embeddings" in url:
                embed_calls += 1
                return {"data": [{"embedding": [0.1, 0.2]}]}
            if "/query" in url:
                return {"matches": []}
            raise AssertionError(f"unexpected URL: {url}")

        with (
            patch.dict(
                "os.environ",
                {"PINECONE_API_KEY": "pc-key", "OPENAI_API_KEY": "oa-key"},
                clear=False,
            ),
            patch("bomba_sr.tools.builtin_pinecone._http_json", side_effect=fake_http),
        ):
            tools = builtin_pinecone_tools(default_index="ublib2", default_namespace="longterm")
            mq_tool = next(t for t in tools if t.name == "pinecone_multi_query")
            mq_tool.execute(
                {
                    "query": "test",
                    "indexes": [
                        {"index_name": "idx-a"},
                        {"index_name": "idx-b"},
                    ],
                },
                _context(),
            )
            self.assertEqual(embed_calls, 1, "Should embed query exactly once for multi-index")


if __name__ == "__main__":
    unittest.main()
