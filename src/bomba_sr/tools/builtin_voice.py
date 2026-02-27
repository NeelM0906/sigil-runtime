from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


BLAND_API_BASE = "https://api.bland.ai/v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
E164_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")


def _http_json(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "sigil-runtime/1.0",
        "authorization": api_key,
    }
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    if not body.strip():
        return {}
    return json.loads(body)


def _require_api_key() -> str:
    import os

    api_key = os.getenv("BLAND_API_KEY", "").strip()
    if not api_key:
        raise ValueError("BLAND_API_KEY is required for voice tools")
    return api_key


def _safe_call_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    allowlist = (
        "status",
        "pathway_id",
        "pathway_name",
        "from_number",
        "to_number",
        "created_at",
        "ended_at",
        "ended_reason",
        "call_length",
    )
    return {key: payload[key] for key in allowlist if key in payload}


def _require_safe_identifier(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    if not SAFE_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(f"{field_name} contains invalid characters")
    return cleaned


def _require_e164_phone(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("to_number is required")
    if not E164_PATTERN.fullmatch(cleaned):
        raise ValueError("to_number must be E.164 formatted (for example: +12015550123)")
    return cleaned


def _list_calls(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    api_key = _require_api_key()
    limit = max(1, min(100, int(arguments.get("limit") or 20)))
    date_filter = str(arguments.get("date_filter") or "").strip()
    pathway_id = str(arguments.get("pathway_id") or "").strip()
    query = {"limit": str(limit)}
    if date_filter:
        query["date_filter"] = date_filter
    if pathway_id:
        query["pathway_id"] = _require_safe_identifier(pathway_id, "pathway_id")
    url = BLAND_API_BASE + "/calls?" + urllib.parse.urlencode(query)
    payload = _http_json("GET", url, api_key=api_key)
    calls = payload.get("calls")
    if not isinstance(calls, list):
        calls = payload.get("data") if isinstance(payload.get("data"), list) else []
    items: list[dict[str, Any]] = []
    for entry in calls:
        if not isinstance(entry, dict):
            continue
        items.append(
            {
                "call_id": str(entry.get("call_id") or entry.get("id") or ""),
                "from_number": str(entry.get("from_number") or entry.get("from") or ""),
                "to_number": str(entry.get("to_number") or entry.get("to") or ""),
                "duration": entry.get("duration"),
                "pathway_name": str(entry.get("pathway_name") or entry.get("pathway") or ""),
                "created_at": str(entry.get("created_at") or ""),
                "status": str(entry.get("status") or ""),
            }
        )
    return {"calls": items}


def _get_transcript(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    api_key = _require_api_key()
    call_id = _require_safe_identifier(str(arguments.get("call_id") or ""), "call_id")
    payload = _http_json(
        "GET",
        f"{BLAND_API_BASE}/calls/{urllib.parse.quote(call_id, safe='')}",
        api_key=api_key,
    )
    transcript = payload.get("transcript")
    if not isinstance(transcript, list):
        transcript = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    return {
        "call_id": call_id,
        "transcript": transcript,
        "duration": payload.get("duration"),
        "metadata": _safe_call_metadata(payload),
    }


def _make_call(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = context
    api_key = _require_api_key()
    to_number = _require_e164_phone(str(arguments.get("to_number") or ""))
    pathway_id = _require_safe_identifier(str(arguments.get("pathway_id") or ""), "pathway_id")
    dynamic_data = arguments.get("dynamic_data")
    if dynamic_data is not None and not isinstance(dynamic_data, dict):
        raise ValueError("dynamic_data must be an object")
    payload = {
        "phone_number": to_number,
        "pathway_id": pathway_id,
    }
    if isinstance(dynamic_data, dict):
        payload["dynamic_data"] = dynamic_data
    response = _http_json("POST", f"{BLAND_API_BASE}/calls", api_key=api_key, payload=payload)
    return {
        "call_id": str(response.get("call_id") or response.get("id") or ""),
        "status": str(response.get("status") or "queued"),
    }


def _list_pathways(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    _ = arguments
    _ = context
    api_key = _require_api_key()
    payload = _http_json("GET", f"{BLAND_API_BASE}/pathways", api_key=api_key)
    pathways = payload.get("pathways")
    if not isinstance(pathways, list):
        pathways = payload.get("data") if isinstance(payload.get("data"), list) else []
    out: list[dict[str, str]] = []
    for item in pathways:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "pathway_id": str(item.get("pathway_id") or item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
            }
        )
    return {"pathways": out}


def builtin_voice_tools(provider: str = "bland") -> list[ToolDefinition]:
    if provider.strip().lower() != "bland":
        return []
    return [
        ToolDefinition(
            name="voice_list_calls",
            description="List recent Bland.ai calls with optional filters.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                    "date_filter": {"type": "string"},
                    "pathway_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_calls,
        ),
        ToolDefinition(
            name="voice_get_transcript",
            description="Fetch a call transcript from Bland.ai.",
            parameters={
                "type": "object",
                "properties": {"call_id": {"type": "string"}},
                "required": ["call_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_get_transcript,
        ),
        ToolDefinition(
            name="voice_make_call",
            description="Trigger an outbound phone call through Bland.ai.",
            parameters={
                "type": "object",
                "properties": {
                    "to_number": {"type": "string"},
                    "pathway_id": {"type": "string"},
                    "dynamic_data": {"type": "object"},
                },
                "required": ["to_number", "pathway_id"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_make_call,
        ),
        ToolDefinition(
            name="voice_list_pathways",
            description="List available Bland.ai pathways.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            risk_level="low",
            action_type="read",
            execute=_list_pathways,
        ),
    ]
