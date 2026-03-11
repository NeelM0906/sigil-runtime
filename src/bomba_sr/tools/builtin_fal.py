from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bomba_sr.artifacts.store import ArtifactStore
from bomba_sr.tools.base import ToolContext, ToolDefinition


FAL_QUEUE_BASE = "https://queue.fal.run"
SAFE_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
VIDEO_EXTS = (".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _fal_api_key() -> str:
    api_key = os.getenv("FAL_KEY_NEW", "").strip() or os.getenv("FAL_KEY", "").strip()
    if not api_key:
        raise ValueError("FAL_KEY or FAL_KEY_NEW is required for Fal tools")
    return api_key


def _require_model_id(value: str) -> str:
    model_id = value.strip().strip("/")
    if not model_id:
        raise ValueError("model_id is required")
    if not SAFE_MODEL_RE.fullmatch(model_id):
        raise ValueError("model_id contains invalid characters")
    return model_id


def _fal_headers(
    api_key: str,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {api_key}",
        "User-Agent": "sigil-runtime/1.0",
    }
    if extra:
        headers.update(extra)
    return headers


def _http_json(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    data = None
    headers = _fal_headers(api_key, extra=extra_headers)
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
        except OSError:
            error_body = ""
        detail = f": {error_body[:300]}" if error_body else ""
        raise ValueError(f"Fal request failed (HTTP {exc.code}){detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Fal request failed: {exc.reason}") from exc
    if not text.strip():
        return {}
    try:
        payload_json = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Fal returned invalid JSON") from exc
    if not isinstance(payload_json, dict):
        raise ValueError("Fal returned an unexpected response shape")
    return payload_json


def _download_binary(url: str, *, api_key: str, timeout: int = 300) -> tuple[bytes, str]:
    headers = {"User-Agent": "sigil-runtime/1.0"}
    # Signed Fal URLs typically do not require auth, but including the key keeps
    # Fal-hosted storage endpoints readable when authorization is enforced.
    headers["Authorization"] = f"Key {api_key}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            mime_type = resp.headers.get_content_type() or "application/octet-stream"
            return data, mime_type
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Fal media download failed (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Fal media download failed: {exc.reason}") from exc


def _queue_endpoint(model_id: str) -> str:
    return f"{FAL_QUEUE_BASE}/{urllib.parse.quote(model_id, safe='/')}"


def _request_status_url(model_id: str, request_id: str) -> str:
    base = _queue_endpoint(model_id)
    return f"{base}/requests/{urllib.parse.quote(request_id, safe='')}/status"


def _request_result_url(model_id: str, request_id: str) -> str:
    base = _queue_endpoint(model_id)
    return f"{base}/requests/{urllib.parse.quote(request_id, safe='')}"


def _build_input(arguments: dict[str, Any]) -> dict[str, Any]:
    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("prompt is required")
    payload: dict[str, Any] = {"prompt": prompt}
    passthrough = (
        "negative_prompt",
        "image_url",
        "seed",
        "duration",
        "aspect_ratio",
        "resolution",
        "num_frames",
        "fps",
    )
    for key in passthrough:
        value = arguments.get(key)
        if value is None or value == "":
            continue
        payload[key] = value
    extra_input = arguments.get("extra_input") or {}
    if extra_input:
        if not isinstance(extra_input, dict):
            raise ValueError("extra_input must be an object")
        payload.update(extra_input)
    return payload


def _bool_arg(arguments: dict[str, Any], key: str, default: bool) -> bool:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "off", ""}


def _extract_logs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    logs = payload.get("logs")
    if isinstance(logs, list):
        return [item for item in logs if isinstance(item, dict)]
    return []


def _infer_media_kind(url: str, key_name: str = "", mime_type: str = "") -> str | None:
    url_path = urllib.parse.urlparse(url).path.lower()
    if mime_type.startswith("video/") or key_name.lower().startswith("video") or url_path.endswith(VIDEO_EXTS):
        return "video"
    if mime_type == "image/gif" or url_path.endswith(".gif"):
        return "gif"
    if mime_type.startswith("image/") or key_name.lower().startswith("image") or url_path.endswith(IMAGE_EXTS):
        return "image"
    return None


def _collect_media_urls(node: Any, path: tuple[str, ...] = ()) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = path + (str(key),)
            if isinstance(value, str) and URL_RE.match(value):
                kind = _infer_media_kind(value, key_name=str(key))
                if kind:
                    found.append({"kind": kind, "url": value, "path": ".".join(next_path)})
            else:
                found.extend(_collect_media_urls(value, next_path))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_collect_media_urls(value, path + (str(index),)))
    return found


def _artifact_filename(kind: str, url: str, mime_type: str, ordinal: int) -> str:
    parsed = urllib.parse.urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if not ext:
        guessed = mimetypes.guess_extension(mime_type or "")
        ext = guessed or (".mp4" if kind == "video" else ".gif" if kind == "gif" else ".png")
    return f"fal-{kind}-{ordinal}{ext}"


def _artifact_store_for_context(context: ToolContext) -> ArtifactStore:
    return ArtifactStore(context.db, context.db.path.parent / "artifacts")


def _ensure_request_store(context: ToolContext) -> None:
    context.db.execute(
        """
        CREATE TABLE IF NOT EXISTS fal_requests (
          request_id TEXT PRIMARY KEY,
          model_id TEXT NOT NULL,
          status_url TEXT NOT NULL,
          response_url TEXT NOT NULL,
          cancel_url TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    context.db.commit()


def _save_request_meta(
    context: ToolContext,
    *,
    request_id: str,
    model_id: str,
    status_url: str,
    response_url: str,
    cancel_url: str,
) -> None:
    _ensure_request_store(context)
    context.db.execute(
        """
        INSERT INTO fal_requests (request_id, model_id, status_url, response_url, cancel_url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(request_id) DO UPDATE SET
          model_id = excluded.model_id,
          status_url = excluded.status_url,
          response_url = excluded.response_url,
          cancel_url = excluded.cancel_url
        """,
        (request_id, model_id, status_url, response_url, cancel_url),
    )
    context.db.commit()


def _load_request_meta(context: ToolContext, request_id: str) -> dict[str, str] | None:
    _ensure_request_store(context)
    row = context.db.execute(
        "SELECT request_id, model_id, status_url, response_url, cancel_url FROM fal_requests WHERE request_id = ?",
        (request_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "request_id": str(row["request_id"]),
        "model_id": str(row["model_id"]),
        "status_url": str(row["status_url"]),
        "response_url": str(row["response_url"]),
        "cancel_url": str(row["cancel_url"] or ""),
    }


def _register_media_artifacts(
    *,
    context: ToolContext,
    model_id: str,
    request_id: str,
    response_payload: dict[str, Any],
    prompt: str,
    api_key: str,
) -> list[dict[str, Any]]:
    store = _artifact_store_for_context(context)
    media = _collect_media_urls(response_payload)
    seen: set[str] = set()
    artifacts: list[dict[str, Any]] = []
    ordinal = 0
    for item in media:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        ordinal += 1
        data, mime_type = _download_binary(url, api_key=api_key)
        kind = _infer_media_kind(url, key_name=item.get("path", ""), mime_type=mime_type) or "video"
        title = f"Fal {kind} {ordinal}: {prompt[:80]}".strip()
        filename = _artifact_filename(kind, url, mime_type, ordinal)
        record = store.create_binary_artifact(
            tenant_id=context.tenant_id,
            session_id=context.session_id,
            turn_id=context.turn_id,
            project_id=None,
            task_id=None,
            artifact_type=kind if kind in {"video", "gif", "image"} else "video",
            title=title,
            data=data,
            filename=filename,
            created_by=f"fal:{model_id}",
        )
        artifacts.append(
            {
                "artifact_id": record.artifact_id,
                "type": record.artifact_type,
                "title": record.title,
                "path": record.path,
                "mime_type": record.mime_type,
                "file_size": record.file_size,
                "source_url": url,
                "request_id": request_id,
            }
        )
    return artifacts


def _result_summary(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response")
    if not isinstance(response, dict):
        return {"status": str(payload.get("status") or ""), "response": response}
    media = _collect_media_urls(response)
    return {
        "status": str(payload.get("status") or ""),
        "media_count": len(media),
        "media": media[:5],
    }


def _generate_video(arguments: dict[str, Any], context: ToolContext, *, default_model_id: str) -> dict[str, Any]:
    api_key = _fal_api_key()
    model_id = _require_model_id(str(arguments.get("model_id") or default_model_id))
    payload = _build_input(arguments)
    request_timeout = max(1, min(120, int(arguments.get("request_timeout_seconds") or 30)))
    lifecycle_seconds = max(300, min(7 * 24 * 3600, int(arguments.get("object_lifecycle_seconds") or 24 * 3600)))
    wait_for_completion = _bool_arg(arguments, "wait_for_completion", False)
    timeout_seconds = max(5, min(900, int(arguments.get("timeout_seconds") or 240)))
    poll_interval_seconds = max(1, min(30, int(arguments.get("poll_interval_seconds") or 5)))

    submit = _http_json(
        "POST",
        _queue_endpoint(model_id),
        api_key=api_key,
        payload=payload,
        extra_headers={
            "X-Fal-Request-Timeout": str(request_timeout),
            "X-Fal-Object-Lifecycle-Preference": json.dumps(
                {"expiration_duration_seconds": lifecycle_seconds},
                separators=(",", ":"),
            ),
        },
        timeout=max(60, request_timeout + 15),
    )
    request_id = str(submit.get("request_id") or "").strip()
    if not request_id:
        raise ValueError("Fal queue response did not include request_id")

    status_url = str(submit.get("status_url") or _request_status_url(model_id, request_id))
    response_url = str(submit.get("response_url") or _request_result_url(model_id, request_id))
    base_result = {
        "model_id": model_id,
        "request_id": request_id,
        "status_url": status_url,
        "response_url": response_url,
        "cancel_url": str(submit.get("cancel_url") or ""),
    }
    _save_request_meta(
        context,
        request_id=request_id,
        model_id=model_id,
        status_url=status_url,
        response_url=response_url,
        cancel_url=base_result["cancel_url"],
    )
    if not wait_for_completion:
        return {**base_result, "status": "QUEUED"}

    deadline = time.time() + timeout_seconds
    last_status: dict[str, Any] = {}
    while time.time() < deadline:
        last_status = _http_json("GET", f"{status_url}?logs=1", api_key=api_key, timeout=90)
        status = str(last_status.get("status") or "").upper()
        if status == "COMPLETED":
            result = _http_json("GET", response_url, api_key=api_key, timeout=180)
            artifacts = _register_media_artifacts(
                context=context,
                model_id=model_id,
                request_id=request_id,
                response_payload=result.get("response") if isinstance(result.get("response"), dict) else result,
                prompt=str(payload.get("prompt") or ""),
                api_key=api_key,
            )
            return {
                **base_result,
                "status": status,
                "logs": _extract_logs(last_status),
                "artifacts": artifacts,
                "result": result,
                "summary": _result_summary(result),
            }
        if status in {"FAILED", "ERROR", "CANCELLED"}:
            return {
                **base_result,
                "status": status,
                "logs": _extract_logs(last_status),
                "error": last_status.get("error") or last_status,
            }
        time.sleep(poll_interval_seconds)

    return {
        **base_result,
        "status": str(last_status.get("status") or "IN_PROGRESS"),
        "logs": _extract_logs(last_status),
        "message": f"Fal request still running after {timeout_seconds} seconds. Use fal_request_status to continue polling.",
    }


def _request_status(arguments: dict[str, Any], context: ToolContext, *, default_model_id: str) -> dict[str, Any]:
    api_key = _fal_api_key()
    request_id = str(arguments.get("request_id") or "").strip()
    if not request_id:
        raise ValueError("request_id is required")
    stored = _load_request_meta(context, request_id)
    model_id = _require_model_id(str(arguments.get("model_id") or (stored or {}).get("model_id") or default_model_id))
    fetch_result = _bool_arg(arguments, "fetch_result", True)
    status_url = str(arguments.get("status_url") or (stored or {}).get("status_url") or _request_status_url(model_id, request_id))
    response_url = str(arguments.get("response_url") or (stored or {}).get("response_url") or _request_result_url(model_id, request_id))
    status_payload = _http_json("GET", f"{status_url}?logs=1", api_key=api_key, timeout=90)
    status = str(status_payload.get("status") or "").upper()
    result: dict[str, Any] = {
        "model_id": model_id,
        "request_id": request_id,
        "status": status,
        "status_url": status_url,
        "response_url": response_url,
        "logs": _extract_logs(status_payload),
    }
    if status == "COMPLETED" and fetch_result:
        response_payload = _http_json("GET", response_url, api_key=api_key, timeout=180)
        artifacts = _register_media_artifacts(
            context=context,
            model_id=model_id,
            request_id=request_id,
            response_payload=response_payload.get("response") if isinstance(response_payload.get("response"), dict) else response_payload,
            prompt=str(arguments.get("prompt") or f"Fal request {request_id}"),
            api_key=api_key,
        )
        result["artifacts"] = artifacts
        result["result"] = response_payload
        result["summary"] = _result_summary(response_payload)
    return result


def builtin_fal_tools(default_video_model: str) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="fal_video_generate",
            description="Generate a video with Fal.ai from a prompt. By default this queues the request and returns immediately with the request id; set wait_for_completion=true if you want the tool to poll and save the finished media as a dashboard artifact in the same turn.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The video generation prompt."},
                    "model_id": {"type": "string", "description": "Fal model id. Defaults to the configured text-to-video model."},
                    "image_url": {"type": "string", "description": "Optional source image URL for image-to-video models."},
                    "negative_prompt": {"type": "string", "description": "Optional negative prompt."},
                    "aspect_ratio": {"type": "string", "description": "Optional aspect ratio, such as 16:9 or 9:16."},
                    "duration": {"type": ["integer", "number"], "description": "Optional target duration in seconds if the model supports it."},
                    "resolution": {"type": "string", "description": "Optional resolution preset accepted by the model."},
                    "seed": {"type": "integer", "description": "Optional generation seed."},
                    "fps": {"type": "integer", "description": "Optional target fps if the model supports it."},
                    "num_frames": {"type": "integer", "description": "Optional frame count if the model supports it."},
                    "extra_input": {"type": "object", "description": "Additional model-specific Fal input fields."},
                    "wait_for_completion": {"type": "boolean", "description": "Wait for completion and download the result into artifacts (default: false)."},
                    "timeout_seconds": {"type": "integer", "description": "Maximum local polling time before returning an in-progress request."},
                    "poll_interval_seconds": {"type": "integer", "description": "Polling interval while waiting for completion."},
                    "request_timeout_seconds": {"type": "integer", "description": "Fal queue start timeout header in seconds."},
                    "object_lifecycle_seconds": {"type": "integer", "description": "How long generated Fal objects should remain available remotely."},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="execute",
            execute=lambda arguments, context: _generate_video(arguments, context, default_model_id=default_video_model),
        ),
        ToolDefinition(
            name="fal_request_status",
            description="Check the status of a Fal request and fetch its generated media into dashboard artifacts when complete.",
            parameters={
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "Fal queue request id."},
                    "model_id": {"type": "string", "description": "Fal model id used for the request."},
                    "fetch_result": {"type": "boolean", "description": "Download and register generated media if the request is complete (default: true)."},
                    "prompt": {"type": "string", "description": "Optional prompt label used when naming artifacts."},
                },
                "required": ["request_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=lambda arguments, context: _request_status(arguments, context, default_model_id=default_video_model),
        ),
    ]
