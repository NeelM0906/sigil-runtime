#!/usr/bin/env python3
"""
fal.ai Unified Video & Image Generation CLI
Usage:
    python3 fal_generate.py video --prompt "..." [--model kling-v2] [--duration 5] [--image path] [--output path]
    python3 fal_generate.py image --prompt "..." [--model flux-dev] [--size landscape_4_3] [--output path]
    python3 fal_generate.py depth --video path [--output path]
    python3 fal_generate.py models                  # List available models
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime

from bomba_sr.openclaw.script_support import load_portable_env

load_portable_env(Path(__file__))

try:
    import fal_client
except ImportError:
    print("ERROR: fal-client not installed. Run: pip install fal-client")
    sys.exit(1)

# ── Model Registry ──────────────────────────────────────────────────────────

VIDEO_MODELS = {
    "kling-v2": {
        "fal_id": "fal-ai/kling-video/v2/master/text-to-video",
        "fal_id_i2v": "fal-ai/kling-video/v2/master/image-to-video",
        "name": "Kling V2 Master",
        "max_duration": 10,
        "default_duration": 5,
    },
    "kling-v2-turbo": {
        "fal_id": "fal-ai/kling-video/v2.5/turbo/text-to-video",
        "fal_id_i2v": "fal-ai/kling-video/v2.5/turbo/image-to-video",
        "name": "Kling V2.5 Turbo",
        "max_duration": 10,
        "default_duration": 5,
    },
    "minimax-video": {
        "fal_id": "fal-ai/minimax-video/video-01-live/text-to-video",
        "fal_id_i2v": "fal-ai/minimax-video/video-01-live/image-to-video",
        "name": "MiniMax Hailuo",
        "max_duration": 6,
        "default_duration": 6,
    },
    "ltx-video": {
        "fal_id": "fal-ai/ltx-video-v2",
        "name": "LTX Video v2",
        "max_duration": 5,
        "default_duration": 5,
    },
    "wan-video": {
        "fal_id": "fal-ai/wan-t2v",
        "fal_id_i2v": "fal-ai/wan-i2v",
        "name": "Wan 2.6",
        "max_duration": 5,
        "default_duration": 5,
    },
    "pika-v2": {
        "fal_id": "fal-ai/pika/v2.2/text-to-video",
        "fal_id_i2v": "fal-ai/pika/v2.2/image-to-video",
        "name": "Pika 2.2",
        "max_duration": 4,
        "default_duration": 4,
    },
}

IMAGE_MODELS = {
    "flux-dev": {
        "fal_id": "fal-ai/flux/dev",
        "name": "FLUX.1 Dev",
    },
    "flux-schnell": {
        "fal_id": "fal-ai/flux/schnell",
        "name": "FLUX.1 Schnell",
    },
    "flux-pro": {
        "fal_id": "fal-ai/flux-pro/v1.1",
        "name": "FLUX Pro 1.1",
    },
    "seedream": {
        "fal_id": "fal-ai/seedream-3",
        "name": "Seedream 3",
    },
}

ANALYSIS_MODELS = {
    "depth": {
        "fal_id": "fal-ai/video-depth-anything/v2",
        "name": "Video Depth Anything V2",
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(os.getenv("FAL_OUTPUT_DIR", "/tmp/fal_output"))

def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url: str, output_path: str) -> str:
    """Download a file from URL to local path."""
    print(f"  Downloading → {output_path}")
    urllib.request.urlretrieve(url, output_path)
    size = os.path.getsize(output_path)
    print(f"  ✅ Saved ({size:,} bytes)")
    return output_path

def upload_image(image_path: str) -> str:
    """Upload a local image to fal storage for use as input."""
    print(f"  Uploading image: {image_path}")
    url = fal_client.upload_file(image_path)
    print(f"  ✅ Uploaded → {url}")
    return url

def log_result(command: str, model: str, prompt: str, result: dict, output_path: str):
    """Log generation result to a JSON file."""
    ensure_output_dir()
    log_file = OUTPUT_DIR / "generation_log.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "model": model,
        "prompt": prompt,
        "output_path": output_path,
        "result_keys": list(result.keys()) if isinstance(result, dict) else str(type(result)),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

def on_queue_update(update):
    """Callback for queue status updates."""
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print(f"  ⏳ {log['message']}")

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_video(args):
    """Generate a video from text or image."""
    model_key = args.model or "kling-v2"
    model = VIDEO_MODELS.get(model_key)
    if not model:
        print(f"ERROR: Unknown video model '{model_key}'. Available: {', '.join(VIDEO_MODELS.keys())}")
        sys.exit(1)

    duration = args.duration or model["default_duration"]
    if duration > model["max_duration"]:
        print(f"WARNING: Duration {duration}s exceeds max {model['max_duration']}s for {model['name']}. Capping.")
        duration = model["max_duration"]

    # Determine if text-to-video or image-to-video
    if args.image:
        fal_id = model.get("fal_id_i2v", model["fal_id"])
        image_url = upload_image(args.image)
        arguments = {
            "prompt": args.prompt or "",
            "image_url": image_url,
            "duration": str(duration),
        }
        mode = "image-to-video"
    else:
        if not args.prompt:
            print("ERROR: --prompt is required for text-to-video")
            sys.exit(1)
        fal_id = model["fal_id"]
        arguments = {
            "prompt": args.prompt,
            "duration": str(duration),
        }
        mode = "text-to-video"

    if args.aspect_ratio:
        arguments["aspect_ratio"] = args.aspect_ratio

    print(f"\n🎬 Generating video ({mode})")
    print(f"  Model: {model['name']} ({model_key})")
    print(f"  Prompt: {args.prompt or '(from image)'}")
    print(f"  Duration: {duration}s")
    print(f"  fal endpoint: {fal_id}")
    print()

    start = time.time()
    result = fal_client.subscribe(
        fal_id,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    elapsed = time.time() - start

    print(f"\n✅ Generated in {elapsed:.1f}s")

    # Extract video URL from result
    video_url = None
    if isinstance(result, dict):
        if "video" in result:
            video_url = result["video"].get("url") if isinstance(result["video"], dict) else result["video"]
        elif "video_url" in result:
            video_url = result["video_url"]
        elif "output" in result:
            out = result["output"]
            if isinstance(out, list) and len(out) > 0:
                video_url = out[0] if isinstance(out[0], str) else out[0].get("url")
            elif isinstance(out, dict):
                video_url = out.get("url") or out.get("video_url")
            elif isinstance(out, str):
                video_url = out

    if not video_url:
        print("  ⚠️  Could not extract video URL from result.")
        print(f"  Raw result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        print(f"  Full result: {json.dumps(result, indent=2, default=str)[:2000]}")
        return

    print(f"  Video URL: {video_url}")

    # Download
    ensure_output_dir()
    ext = "mp4"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or str(OUTPUT_DIR / f"video_{model_key}_{ts}.{ext}")
    download_file(video_url, output_path)
    log_result("video", model_key, args.prompt or "(image)", result, output_path)
    print(f"\n🎬 Output: {output_path}")


def cmd_image(args):
    """Generate an image from text."""
    model_key = args.model or "flux-dev"
    model = IMAGE_MODELS.get(model_key)
    if not model:
        print(f"ERROR: Unknown image model '{model_key}'. Available: {', '.join(IMAGE_MODELS.keys())}")
        sys.exit(1)

    if not args.prompt:
        print("ERROR: --prompt is required")
        sys.exit(1)

    arguments = {
        "prompt": args.prompt,
    }
    if args.size:
        arguments["image_size"] = args.size
    if args.num_images:
        arguments["num_images"] = args.num_images

    print(f"\n🖼️  Generating image")
    print(f"  Model: {model['name']} ({model_key})")
    print(f"  Prompt: {args.prompt}")
    if args.size:
        print(f"  Size: {args.size}")
    print()

    start = time.time()
    result = fal_client.subscribe(
        model["fal_id"],
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    elapsed = time.time() - start

    print(f"\n✅ Generated in {elapsed:.1f}s")

    # Extract image URL(s)
    images = []
    if isinstance(result, dict):
        if "images" in result:
            for img in result["images"]:
                url = img.get("url") if isinstance(img, dict) else img
                if url:
                    images.append(url)
        elif "image" in result:
            img = result["image"]
            url = img.get("url") if isinstance(img, dict) else img
            if url:
                images.append(url)
        elif "output" in result:
            out = result["output"]
            if isinstance(out, list):
                for item in out:
                    url = item.get("url") if isinstance(item, dict) else item
                    if url:
                        images.append(url)

    if not images:
        print("  ⚠️  Could not extract image URL from result.")
        print(f"  Raw result: {json.dumps(result, indent=2, default=str)[:2000]}")
        return

    ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, url in enumerate(images):
        suffix = f"_{i}" if len(images) > 1 else ""
        output_path = args.output or str(OUTPUT_DIR / f"image_{model_key}_{ts}{suffix}.png")
        download_file(url, output_path)
        log_result("image", model_key, args.prompt, result, output_path)
        print(f"  🖼️  Output: {output_path}")


def cmd_depth(args):
    """Run depth analysis on a video."""
    if not args.video:
        print("ERROR: --video is required")
        sys.exit(1)

    model = ANALYSIS_MODELS["depth"]
    video_url = upload_image(args.video)  # reuse upload for any file

    print(f"\n🔍 Analyzing video depth")
    print(f"  Model: {model['name']}")
    print(f"  Input: {args.video}")
    print()

    start = time.time()
    result = fal_client.subscribe(
        model["fal_id"],
        arguments={"video_url": video_url},
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    elapsed = time.time() - start

    print(f"\n✅ Analyzed in {elapsed:.1f}s")

    # Extract depth video
    depth_url = None
    if isinstance(result, dict):
        if "video" in result:
            depth_url = result["video"].get("url") if isinstance(result["video"], dict) else result["video"]
        elif "depth_video" in result:
            depth_url = result["depth_video"]

    if depth_url:
        ensure_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = args.output or str(OUTPUT_DIR / f"depth_{ts}.mp4")
        download_file(depth_url, output_path)
        print(f"\n🔍 Depth output: {output_path}")
    else:
        print(f"  Result: {json.dumps(result, indent=2, default=str)[:2000]}")


def cmd_models(args):
    """List available models."""
    print("\n🎬 VIDEO GENERATION MODELS")
    print("-" * 70)
    for key, m in VIDEO_MODELS.items():
        i2v = "✅" if "fal_id_i2v" in m else "❌"
        print(f"  {key:<20} {m['name']:<25} max {m['max_duration']}s  i2v: {i2v}")

    print("\n🖼️  IMAGE GENERATION MODELS")
    print("-" * 70)
    for key, m in IMAGE_MODELS.items():
        print(f"  {key:<20} {m['name']:<25}")

    print("\n🔍 ANALYSIS MODELS")
    print("-" * 70)
    for key, m in ANALYSIS_MODELS.items():
        print(f"  {key:<20} {m['name']:<25}")

    print("\nUsage:")
    print("  python3 fal_generate.py video --prompt '...' --model <model>")
    print("  python3 fal_generate.py image --prompt '...' --model <model>")
    print("  python3 fal_generate.py depth --video /path/to/video.mp4")
    print()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="fal.ai Video & Image Generation")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # video
    p_video = subparsers.add_parser("video", help="Generate video")
    p_video.add_argument("--prompt", "-p", type=str, help="Text prompt")
    p_video.add_argument("--model", "-m", type=str, default="kling-v2", help="Model (default: kling-v2)")
    p_video.add_argument("--duration", "-d", type=int, help="Duration in seconds")
    p_video.add_argument("--image", "-i", type=str, help="Input image for image-to-video")
    p_video.add_argument("--aspect-ratio", "-ar", type=str, help="Aspect ratio (e.g. 16:9, 9:16)")
    p_video.add_argument("--output", "-o", type=str, help="Output file path")

    # image
    p_image = subparsers.add_parser("image", help="Generate image")
    p_image.add_argument("--prompt", "-p", type=str, required=True, help="Text prompt")
    p_image.add_argument("--model", "-m", type=str, default="flux-dev", help="Model (default: flux-dev)")
    p_image.add_argument("--size", "-s", type=str, help="Image size (e.g. landscape_4_3, square_hd, portrait_4_3)")
    p_image.add_argument("--num-images", "-n", type=int, default=1, help="Number of images")
    p_image.add_argument("--output", "-o", type=str, help="Output file path")

    # depth
    p_depth = subparsers.add_parser("depth", help="Analyze video depth")
    p_depth.add_argument("--video", "-v", type=str, required=True, help="Input video path")
    p_depth.add_argument("--output", "-o", type=str, help="Output file path")

    # models
    subparsers.add_parser("models", help="List available models")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check API key
    if not os.environ.get("FAL_KEY"):
        print("ERROR: FAL_KEY not set. Add it to the repo .env or export FAL_KEY=[REDACTED]")
        sys.exit(1)

    commands = {
        "video": cmd_video,
        "image": cmd_image,
        "depth": cmd_depth,
        "models": cmd_models,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
