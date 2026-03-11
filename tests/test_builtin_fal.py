from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bomba_sr.artifacts.store import get_artifact_type_info
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_fal import builtin_fal_tools


def _ctx() -> ToolContext:
    tempdir = tempfile.TemporaryDirectory()
    db_path = Path(tempdir.name) / "runtime.db"
    db = RuntimeDB(db_path)
    ctx = ToolContext(
        tenant_id="tenant",
        session_id="session",
        turn_id="turn",
        user_id="user",
        workspace_root=Path.cwd(),
        db=db,
        guard_path=lambda p: Path(p),
    )
    ctx._tempdir = tempdir  # type: ignore[attr-defined]
    return ctx


class FalToolTests(unittest.TestCase):
    def test_video_artifact_type_registered(self) -> None:
        ext, mime, is_binary = get_artifact_type_info("video")
        self.assertEqual(ext, ".mp4")
        self.assertEqual(mime, "video/mp4")
        self.assertTrue(is_binary)

    def test_generate_video_waits_and_registers_artifact(self) -> None:
        context = _ctx()

        def fake_http(method, url, *, api_key, payload=None, extra_headers=None, timeout=180):  # noqa: ANN001
            self.assertEqual(api_key, "fal-key")
            if method == "POST":
                self.assertIn("/fal-ai/wan/v2.2-a14b/text-to-video", url)
                self.assertEqual(payload["prompt"], "launch video")
                self.assertIn("X-Fal-Object-Lifecycle-Preference", extra_headers)
                return {
                    "request_id": "req-1",
                    "status_url": "https://queue.fal.run/fal-ai/wan/v2.2-a14b/text-to-video/requests/req-1/status",
                    "response_url": "https://queue.fal.run/fal-ai/wan/v2.2-a14b/text-to-video/requests/req-1",
                }
            if url.endswith("/status?logs=1"):
                return {"status": "COMPLETED", "logs": [{"message": "done"}]}
            if url.endswith("/requests/req-1"):
                return {
                    "status": "COMPLETED",
                    "response": {
                        "video": {
                            "url": "https://files.fal.media/generated/video.mp4",
                        }
                    },
                }
            raise AssertionError(f"unexpected request {method} {url}")

        with (
            patch.dict("os.environ", {"FAL_KEY": "fal-key"}, clear=False),
            patch("bomba_sr.tools.builtin_fal._http_json", side_effect=fake_http),
            patch("bomba_sr.tools.builtin_fal._download_binary", return_value=(b"video-bytes", "video/mp4")),
        ):
            tool = next(t for t in builtin_fal_tools("fal-ai/wan/v2.2-a14b/text-to-video") if t.name == "fal_video_generate")
            result = tool.execute({"prompt": "launch video", "wait_for_completion": True}, context)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["request_id"], "req-1")
        self.assertEqual(len(result["artifacts"]), 1)
        artifact_path = Path(result["artifacts"][0]["path"])
        self.assertTrue(artifact_path.exists())
        self.assertEqual(artifact_path.read_bytes(), b"video-bytes")
        records = context.db.execute("SELECT artifact_type, title, created_by FROM artifacts").fetchall()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["artifact_type"], "video")
        self.assertEqual(records[0]["created_by"], "fal:fal-ai/wan/v2.2-a14b/text-to-video")
        context.db.close()
        context._tempdir.cleanup()  # type: ignore[attr-defined]

    def test_generate_video_can_return_queued_request(self) -> None:
        context = _ctx()
        with (
            patch.dict("os.environ", {"FAL_KEY_NEW": "fal-key"}, clear=False),
            patch(
                "bomba_sr.tools.builtin_fal._http_json",
                return_value={
                    "request_id": "req-queued",
                    "status_url": "https://queue.fal.run/model/requests/req-queued/status",
                    "response_url": "https://queue.fal.run/model/requests/req-queued",
                },
            ),
        ):
            tool = next(t for t in builtin_fal_tools("fal-ai/wan/v2.2-a14b/text-to-video") if t.name == "fal_video_generate")
            result = tool.execute(
                {"prompt": "launch video", "wait_for_completion": False},
                context,
            )
        self.assertEqual(result["status"], "QUEUED")
        self.assertEqual(result["request_id"], "req-queued")
        row = context.db.execute(
            "SELECT status_url, response_url FROM fal_requests WHERE request_id = ?",
            ("req-queued",),
        ).fetchone()
        self.assertIsNotNone(row)
        context.db.close()
        context._tempdir.cleanup()  # type: ignore[attr-defined]

    def test_request_status_fetches_completed_result(self) -> None:
        context = _ctx()

        def fake_http(method, url, *, api_key, payload=None, extra_headers=None, timeout=180):  # noqa: ANN001
            self.assertEqual(api_key, "fal-key")
            if url.endswith("/status?logs=1"):
                return {"status": "COMPLETED", "logs": [{"message": "done"}]}
            if url.endswith("/requests/req-2"):
                return {
                    "status": "COMPLETED",
                    "response": {
                        "video": {"url": "https://files.fal.media/generated/result.mp4"},
                    },
                }
            raise AssertionError(f"unexpected request {method} {url}")

        with (
            patch.dict("os.environ", {"FAL_KEY": "fal-key"}, clear=False),
            patch("bomba_sr.tools.builtin_fal._http_json", side_effect=fake_http),
            patch("bomba_sr.tools.builtin_fal._download_binary", return_value=(b"video-2", "video/mp4")),
        ):
            tool = next(t for t in builtin_fal_tools("fal-ai/wan/v2.2-a14b/text-to-video") if t.name == "fal_request_status")
            result = tool.execute({"request_id": "req-2"}, context)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(len(result["artifacts"]), 1)
        self.assertEqual(Path(result["artifacts"][0]["path"]).read_bytes(), b"video-2")
        context.db.close()
        context._tempdir.cleanup()  # type: ignore[attr-defined]

    def test_missing_key_raises(self) -> None:
        context = _ctx()
        with patch.dict("os.environ", {"FAL_KEY": "", "FAL_KEY_NEW": ""}, clear=False):
            tool = next(t for t in builtin_fal_tools("fal-ai/wan/v2.2-a14b/text-to-video") if t.name == "fal_video_generate")
            with self.assertRaises(ValueError):
                tool.execute({"prompt": "launch video"}, context)
        context.db.close()
        context._tempdir.cleanup()  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
