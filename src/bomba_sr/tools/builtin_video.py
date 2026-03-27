"""ACT-I Creative Forge — Video Generation Tools.

Integrates the fal.ai Kling v3 Pro pipeline as native runtime tools.
Supports text-to-video generation with the ACT-I style anchor,
character library, and batch scene generation.
"""
from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# STYLE ANCHOR — appended to every prompt
# ═══════════════════════════════════════════════════════
STYLE_ANCHOR = (
    "Disney Pixar DreamWorks Zootopia-style 3D cartoon animation. "
    "ALL characters are CARTOON ANIMALS with FULL ANIMAL FACES. "
    "NOT humans. NEVER human faces. NEVER human people anywhere. "
    "ALL animals STANDING UPRIGHT BIPEDAL wearing CLOTHES. "
    "Warm amber cinematic lighting. Soft shadows. "
    "Semi-realistic fur texturing. 16:9. No text on screen."
)

# ═══════════════════════════════════════════════════════
# CHARACTER LIBRARY
# ═══════════════════════════════════════════════════════
CHARACTERS = {
    "sean": "A MALE anthropomorphic LION with GOLDEN-ORANGE fur and wild REDDISH-ORANGE mane with silver threads. BLIND with ROUND DARK SUNGLASSES. Wearing a charcoal suit. Standing UPRIGHT BIPEDAL",
    "tony": "A GIGANTIC MALE anthropomorphic LION TWICE AS TALL AND WIDE as every other character. DARK CHOCOLATE BROWN fur. Enormous PITCH BLACK mane like a thundercloud. BARREL CHEST straining against a tight BLACK V-NECK SHIRT. Standing UPRIGHT BIPEDAL",
    "dean": "A thin elegant MALE anthropomorphic LION with COMPLETELY JET BLACK fur head to toe. Slicked-back shiny black mane. NAVY BLUE BLAZER over CHARCOAL TURTLENECK with WHITE POCKET SQUARE. Piercing AMBER-ORANGE eyes. Standing UPRIGHT BIPEDAL",
    "tyler": "A SMALL CHILD-SIZED MALE anthropomorphic LION CUB HALF THE HEIGHT of adults. Light golden fur, NO MANE, bright blue eyes, oversized blue hoodie. Standing UPRIGHT BIPEDAL",
    "mylo": "A small adorable FEMALE anthropomorphic MOUSE with cream peach fur, BIG ROUND ORANGE EARS, warm brown eyes with eyelashes, small pink nose, wearing an orange polka dot shirt with an orange bow tie. Standing UPRIGHT BIPEDAL",
    "athena": "A tall elegant FEMALE anthropomorphic OWL, silver-white plumage, wise golden eyes, wearing a flowing royal blue dress with subtle gold lightning bolt patterns, a small golden crown with an A symbol. Standing UPRIGHT BIPEDAL",
    "kira": "A radiant FEMALE anthropomorphic DOVE, pure white feathers that glow softly with warm golden light, gentle eyes, wearing flowing soft gold and white robes. Standing UPRIGHT BIPEDAL",
    "sage": "A graceful FEMALE anthropomorphic SWAN. Pure white feathers, long elegant neck. Wearing a flowing cream dress with gold accents. Standing UPRIGHT BIPEDAL",
    "mary": "A glamorous FEMALE anthropomorphic PEACOCK. Brilliant iridescent plumage, tail fanned. Wearing an emerald blazer with gold jewelry and Louis Vuitton bag. Standing UPRIGHT BIPEDAL",
    "lyor": "A MALE anthropomorphic PEREGRINE FALCON. Sharp angular face, dark grey-brown feathers, sharp hooked beak. Wearing a slim black tech jacket with blue circuit accents. Standing UPRIGHT BIPEDAL",
    "dan": "A lean athletic MALE anthropomorphic CHEETAH. Spotted golden fur with black tear marks from eyes to mouth. Wearing a stylish fitted black blazer over a dark shirt. Standing UPRIGHT BIPEDAL",
}

KLING_ENDPOINT = "fal-ai/kling-video/v3/pro/text-to-video"
QUEUE_URL = f"https://queue.fal.run/{KLING_ENDPOINT}"


def _get_fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY environment variable not set")
    return key


def _submit_and_poll(prompt: str, duration: str = "10", fal_key: str = "",
                     timeout_seconds: int = 600) -> dict:
    """Submit a video generation request and poll for completion."""
    import requests

    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9",
        "generate_audio": True,
    }

    resp = requests.post(QUEUE_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        return {"error": f"Submit failed: HTTP {resp.status_code}", "status": "failed"}

    data = resp.json()
    request_id = data.get("request_id", "")
    status_url = data.get("status_url", "")
    response_url = data.get("response_url", "")

    # Poll
    max_polls = timeout_seconds // 5
    for i in range(max_polls):
        time.sleep(5)
        try:
            sr = requests.get(status_url, headers={"Authorization": f"Key {fal_key}"}, timeout=15)
            sd = sr.json()
            status = sd.get("status", "")
            if status == "COMPLETED":
                rr = requests.get(response_url, headers={"Authorization": f"Key {fal_key}"}, timeout=30)
                result = rr.json()
                video_url = result.get("video", {}).get("url", "")
                return {"video_url": video_url, "request_id": request_id, "status": "completed"}
            elif status == "FAILED":
                return {"error": f"Generation failed: {sd}", "request_id": request_id, "status": "failed"}
        except Exception as exc:
            log.debug("Poll error for %s: %s", request_id[:12], exc)

    return {"error": "Timeout waiting for video", "request_id": request_id, "status": "timeout"}


def _generate_video(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Generate a single video clip using Kling v3 Pro via fal.ai."""
    import requests

    prompt = str(arguments.get("prompt") or "").strip()
    title = str(arguments.get("title") or "generated-video").strip()
    duration = "10"  # Always 10s — 5s clips have NO AUDIO
    use_style_anchor = arguments.get("style_anchor", True)
    character_names = arguments.get("characters") or []

    if not prompt:
        raise ValueError("prompt is required")

    # Inject character descriptions
    for char_name in character_names:
        char_desc = CHARACTERS.get(char_name.lower())
        if char_desc and char_name.lower() not in prompt.lower():
            prompt = f"{char_desc}. {prompt}"

    # Append style anchor
    if use_style_anchor and "UPRIGHT BIPEDAL" not in prompt:
        prompt = f"{prompt} {STYLE_ANCHOR}"

    fal_key = _get_fal_key()
    log.info("[VIDEO] Generating: %s (duration=%s)", title, duration)

    result = _submit_and_poll(prompt, duration=duration, fal_key=fal_key)

    if result.get("status") != "completed" or not result.get("video_url"):
        return {"error": result.get("error", "Generation failed"), "status": result["status"]}

    # Download video
    video_url = result["video_url"]
    vid_resp = requests.get(video_url, timeout=60)

    # Save to workspace deliverables
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title).strip().replace(" ", "-")
    ws_root = context.workspace_root or Path("workspaces/prime")
    deliverables_dir = ws_root / "deliverables"
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    out_path = deliverables_dir / f"{safe_title}.mp4"

    with open(out_path, "wb") as f:
        f.write(vid_resp.content)

    file_size = len(vid_resp.content)
    log.info("[VIDEO] Saved: %s (%d bytes)", out_path, file_size)

    return {
        "status": "completed",
        "file_path": str(out_path),
        "filename": f"{safe_title}.mp4",
        "file_size": file_size,
        "title": title,
        "duration": duration,
        "request_id": result.get("request_id", ""),
        "_is_deliverable": True,
        "mime_type": "video/mp4",
    }


def _generate_batch(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Generate multiple video scenes in parallel."""
    import requests

    scenes = arguments.get("scenes") or []
    max_workers = min(int(arguments.get("max_workers") or 5), 20)

    if not scenes:
        raise ValueError("scenes list is required")

    fal_key = _get_fal_key()
    ws_root = context.workspace_root or Path("workspaces/prime")
    deliverables_dir = ws_root / "deliverables"
    deliverables_dir.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []

    def _process_scene(scene):
        scene_id = scene.get("id", f"scene-{len(results)}")
        prompt = scene.get("prompt", "")
        duration = str(scene.get("duration", "10"))
        title = scene.get("title", scene_id)

        if not prompt:
            return {"id": scene_id, "error": "No prompt"}

        # Auto-append style anchor
        if "UPRIGHT BIPEDAL" not in prompt:
            prompt = f"{prompt} {STYLE_ANCHOR}"

        result = _submit_and_poll(prompt, duration=duration, fal_key=fal_key)

        if result.get("status") != "completed" or not result.get("video_url"):
            return {"id": scene_id, "error": result.get("error", "Failed"), "status": result["status"]}

        vid_resp = requests.get(result["video_url"], timeout=60)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "" for c in scene_id)
        out_path = deliverables_dir / f"{safe_id}.mp4"
        with open(out_path, "wb") as f:
            f.write(vid_resp.content)

        return {
            "id": scene_id,
            "title": title,
            "status": "completed",
            "file_path": str(out_path),
            "file_size": len(vid_resp.content),
        }

    log.info("[VIDEO-BATCH] Generating %d scenes (workers=%d)", len(scenes), max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_process_scene, s): s.get("id", i) for i, s in enumerate(scenes)}
        for f in as_completed(futures):
            r = f.result()
            if r.get("error"):
                errors.append(r)
            else:
                results.append(r)

    return {
        "completed": len(results),
        "failed": len(errors),
        "total": len(scenes),
        "results": results,
        "errors": errors,
    }


def _list_characters(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """List available ACT-I character descriptions for video prompts."""
    return {"characters": {k: v for k, v in CHARACTERS.items()}, "style_anchor": STYLE_ANCHOR}


def builtin_video_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="video_generate",
            description=(
                "Generate a video clip using Kling v3 Pro via fal.ai. "
                "Produces 5-10 second animated clips. Use duration=10 for audio. "
                "Saves to workspace/deliverables/ and registers as output."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed scene description. Include character descriptions, camera directions, and action.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the video file (e.g., 'scene01-the-fire')",
                    },
                    "duration": {
                        "type": "string",
                        "enum": ["10"],
                        "description": "Duration in seconds. Always 10 — 5s clips have no audio.",
                    },
                    "characters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Character names to auto-inject descriptions (e.g., ['sean', 'athena'])",
                    },
                    "style_anchor": {
                        "type": "boolean",
                        "description": "Append ACT-I Pixar/Zootopia style anchor (default true)",
                    },
                },
                "required": ["prompt", "title"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_generate_video,
        ),
        ToolDefinition(
            name="video_generate_batch",
            description=(
                "Generate multiple video scenes in parallel. "
                "Each scene gets its own prompt and output file. "
                "Max 20 parallel workers."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "prompt": {"type": "string"},
                                "duration": {"type": "string"},
                            },
                            "required": ["id", "prompt"],
                        },
                        "description": "List of scenes to generate",
                    },
                    "max_workers": {
                        "type": "integer",
                        "description": "Parallel workers (default 5, max 20)",
                    },
                },
                "required": ["scenes"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_generate_batch,
        ),
        ToolDefinition(
            name="video_characters",
            description="List available ACT-I character descriptions and style anchor for video prompts.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            risk_level="low",
            action_type="read",
            execute=_list_characters,
        ),
    ]
