#!/usr/bin/env python3
"""
fal.ai Video Assembly Pipeline
Generate multiple clips and assemble them into a single video with transitions,
text overlays, audio, and more — all programmatically.

Usage:
    python3 fal_assemble.py --config pipeline.json --output final_video.mp4
    python3 fal_assemble.py --scenes scenes.json --output final_video.mp4
    python3 fal_assemble.py example                    # Print example config

Capabilities:
    1. Generate multiple video clips from prompts (via fal.ai)
    2. Generate images and animate them (image-to-video)
    3. Concatenate clips with crossfade transitions
    4. Add text overlays (titles, CTAs, captions)
    5. Add background music / voiceover audio
    6. Add intro/outro cards
    7. Resize/crop for any aspect ratio (16:9, 9:16, 1:1)
    8. Output ready for ads, social, landing pages
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

from bomba_sr.openclaw.script_support import load_portable_env

load_portable_env(Path(__file__))

try:
    import fal_client
except ImportError:
    print("ERROR: fal-client not installed. Run: pip install fal-client")
    sys.exit(1)

OUTPUT_DIR = Path(os.getenv("FAL_OUTPUT_DIR", "/tmp/fal_output"))
WORK_DIR = Path(os.getenv("FAL_ASSEMBLY_DIR", "/tmp/fal_assembly"))

# ── Generation ───────────────────────────────────────────────────────────────

def generate_video_clip(prompt, model="kling-v2", duration=5, image_path=None, aspect_ratio=None):
    """Generate a single video clip via fal.ai."""
    from skills_fal_ai import VIDEO_MODELS
    
    model_info = VIDEO_MODELS.get(model, VIDEO_MODELS["kling-v2"])
    
    if image_path:
        fal_id = model_info.get("fal_id_i2v", model_info["fal_id"])
        image_url = fal_client.upload_file(image_path)
        arguments = {"prompt": prompt or "", "image_url": image_url, "duration": str(duration)}
    else:
        fal_id = model_info["fal_id"]
        arguments = {"prompt": prompt, "duration": str(duration)}
    
    if aspect_ratio:
        arguments["aspect_ratio"] = aspect_ratio
    
    print(f"  🎬 Generating: {prompt[:60]}... ({model}, {duration}s)")
    start = time.time()
    result = fal_client.subscribe(fal_id, arguments=arguments, with_logs=False)
    elapsed = time.time() - start
    
    # Extract video URL
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
    
    if not video_url:
        print(f"    ⚠️ Failed to extract URL. Result: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        return None
    
    # Download
    import urllib.request
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    local_path = str(WORK_DIR / f"clip_{ts}.mp4")
    urllib.request.urlretrieve(video_url, local_path)
    size = os.path.getsize(local_path)
    print(f"    ✅ Done in {elapsed:.1f}s ({size:,} bytes)")
    return local_path


def generate_image(prompt, model="flux-dev", size=None):
    """Generate an image via fal.ai."""
    IMAGE_MODELS = {
        "flux-dev": "fal-ai/flux/dev",
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-pro": "fal-ai/flux-pro/v1.1",
        "seedream": "fal-ai/seedream-3",
    }
    fal_id = IMAGE_MODELS.get(model, IMAGE_MODELS["flux-dev"])
    arguments = {"prompt": prompt}
    if size:
        arguments["image_size"] = size
    
    print(f"  🖼️  Generating image: {prompt[:60]}...")
    result = fal_client.subscribe(fal_id, arguments=arguments, with_logs=False)
    
    image_url = None
    if isinstance(result, dict):
        if "images" in result and result["images"]:
            img = result["images"][0]
            image_url = img.get("url") if isinstance(img, dict) else img
        elif "image" in result:
            img = result["image"]
            image_url = img.get("url") if isinstance(img, dict) else img
    
    if not image_url:
        return None
    
    import urllib.request
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    local_path = str(WORK_DIR / f"img_{ts}.png")
    urllib.request.urlretrieve(image_url, local_path)
    print(f"    ✅ Image saved")
    return local_path


# ── FFmpeg Assembly ──────────────────────────────────────────────────────────

def get_video_duration(path):
    """Get video duration in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def normalize_clip(input_path, output_path, width=1280, height=720, fps=24):
    """Normalize a clip to consistent resolution, fps, and codec."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",  # strip audio for now, add back in final
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def concatenate_clips(clip_paths, output_path, crossfade_duration=0.5):
    """Concatenate clips with optional crossfade transitions."""
    if not clip_paths:
        print("ERROR: No clips to concatenate")
        return None
    
    if len(clip_paths) == 1:
        # Single clip, just copy
        subprocess.run(["cp", clip_paths[0], output_path], check=True)
        return output_path
    
    if crossfade_duration > 0 and len(clip_paths) > 1:
        # Build complex filter for crossfades
        filter_parts = []
        inputs = []
        
        for i, clip in enumerate(clip_paths):
            inputs.extend(["-i", clip])
        
        # Build xfade filter chain
        current = "[0:v]"
        for i in range(1, len(clip_paths)):
            dur = get_video_duration(clip_paths[i-1]) if i == 1 else None
            offset = get_video_duration(clip_paths[i-1]) - crossfade_duration if i == 1 else 0
            
            # Calculate cumulative offset
            total_offset = sum(get_video_duration(clip_paths[j]) for j in range(i)) - (crossfade_duration * i)
            total_offset = max(0, total_offset)
            
            next_input = f"[{i}:v]"
            out_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[outv]"
            filter_parts.append(f"{current}{next_input}xfade=transition=fade:duration={crossfade_duration}:offset={total_offset}{out_label}")
            current = out_label
        
        filter_str = ";".join(filter_parts)
        
        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    else:
        # Simple concat without transitions
        list_file = str(WORK_DIR / "concat_list.txt")
        with open(list_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def add_text_overlay(input_path, output_path, text, position="center", 
                     fontsize=48, fontcolor="white", bg_opacity=0.5,
                     start_time=0, end_time=None):
    """Add text overlay to video."""
    # Position mapping
    pos_map = {
        "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        "top": "x=(w-text_w)/2:y=50",
        "bottom": "x=(w-text_w)/2:y=h-text_h-50",
        "top-left": "x=50:y=50",
        "top-right": "x=w-text_w-50:y=50",
        "bottom-left": "x=50:y=h-text_h-50",
        "bottom-right": "x=w-text_w-50:y=h-text_h-50",
    }
    pos = pos_map.get(position, pos_map["center"])
    
    # Escape text for ffmpeg
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")
    
    # Build drawtext filter
    filter_str = f"drawtext=text='{escaped_text}':fontsize={fontsize}:fontcolor={fontcolor}:{pos}:box=1:boxcolor=black@{bg_opacity}:boxborderw=10"
    
    if end_time:
        filter_str += f":enable='between(t,{start_time},{end_time})'"
    elif start_time > 0:
        filter_str += f":enable='gte(t,{start_time})'"
    
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def add_audio(video_path, audio_path, output_path, volume=1.0, loop_audio=True):
    """Add audio track to video (background music or voiceover)."""
    duration = get_video_duration(video_path)
    
    audio_filter = f"volume={volume}"
    if loop_audio:
        audio_input = ["-stream_loop", "-1", "-i", audio_path]
    else:
        audio_input = ["-i", audio_path]
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
    ] + audio_input + [
        "-filter_complex", f"[1:a]{audio_filter}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def create_title_card(text, output_path, duration=3, width=1280, height=720,
                      fontsize=64, fontcolor="white", bg_color="black"):
    """Create a title card (solid color + text) as a video clip."""
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg_color}:s={width}x{height}:d={duration}:r=24",
        "-vf", f"drawtext=text='{escaped_text}':fontsize={fontsize}:fontcolor={fontcolor}:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def resize_for_platform(input_path, output_path, platform="youtube"):
    """Resize video for specific platform."""
    sizes = {
        "youtube": (1920, 1080),
        "instagram-feed": (1080, 1080),
        "instagram-reel": (1080, 1920),
        "tiktok": (1080, 1920),
        "linkedin": (1920, 1080),
        "facebook": (1280, 720),
        "twitter": (1280, 720),
    }
    w, h = sizes.get(platform, (1280, 720))
    
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


# ── Pipeline Runner ──────────────────────────────────────────────────────────

# Import video models from main script
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


def run_pipeline(config, output_path):
    """Run the full video assembly pipeline from a config."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    scenes = config.get("scenes", [])
    settings = config.get("settings", {})
    
    width = settings.get("width", 1280)
    height = settings.get("height", 720)
    fps = settings.get("fps", 24)
    crossfade = settings.get("crossfade_duration", 0.5)
    
    print(f"\n🎬 VIDEO ASSEMBLY PIPELINE")
    print(f"  Scenes: {len(scenes)}")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Crossfade: {crossfade}s")
    print()
    
    # Step 1: Generate / gather all clips
    clip_paths = []
    for i, scene in enumerate(scenes):
        print(f"\n📍 Scene {i+1}/{len(scenes)}: {scene.get('type', 'video')}")
        
        scene_type = scene.get("type", "video")
        
        if scene_type == "title":
            # Title card
            title_path = str(WORK_DIR / f"title_{i}.mp4")
            create_title_card(
                text=scene["text"],
                output_path=title_path,
                duration=scene.get("duration", 3),
                width=width, height=height,
                fontsize=scene.get("fontsize", 64),
                fontcolor=scene.get("fontcolor", "white"),
                bg_color=scene.get("bg_color", "black"),
            )
            clip_paths.append(title_path)
            
        elif scene_type == "video":
            # Generate video via fal.ai
            clip = generate_video_clip(
                prompt=scene["prompt"],
                model=scene.get("model", "kling-v2"),
                duration=scene.get("duration", 5),
                image_path=scene.get("image"),
                aspect_ratio=scene.get("aspect_ratio"),
            )
            if clip:
                # Normalize
                norm_path = str(WORK_DIR / f"norm_{i}.mp4")
                normalize_clip(clip, norm_path, width, height, fps)
                clip_paths.append(norm_path)
            else:
                print(f"    ⚠️ Skipping failed scene {i+1}")
                
        elif scene_type == "image_to_video":
            # Generate image then animate it
            img_prompt = scene.get("image_prompt", scene.get("prompt", ""))
            img_path = scene.get("image")
            
            if not img_path and img_prompt:
                img_path = generate_image(
                    prompt=img_prompt,
                    model=scene.get("image_model", "flux-dev"),
                    size=scene.get("image_size"),
                )
            
            if img_path:
                clip = generate_video_clip(
                    prompt=scene.get("motion_prompt", "slow cinematic camera movement"),
                    model=scene.get("model", "kling-v2"),
                    duration=scene.get("duration", 5),
                    image_path=img_path,
                )
                if clip:
                    norm_path = str(WORK_DIR / f"norm_{i}.mp4")
                    normalize_clip(clip, norm_path, width, height, fps)
                    clip_paths.append(norm_path)
                    
        elif scene_type == "file":
            # Use existing local video file
            local = scene["path"]
            if os.path.exists(local):
                norm_path = str(WORK_DIR / f"norm_{i}.mp4")
                normalize_clip(local, norm_path, width, height, fps)
                clip_paths.append(norm_path)
            else:
                print(f"    ⚠️ File not found: {local}")
    
    if not clip_paths:
        print("\n❌ No clips generated. Check your config and fal.ai balance.")
        return None
    
    # Step 2: Concatenate clips
    print(f"\n🔗 Assembling {len(clip_paths)} clips...")
    assembled_path = str(WORK_DIR / "assembled.mp4")
    concatenate_clips(clip_paths, assembled_path, crossfade_duration=crossfade)
    
    # Step 3: Add text overlays
    current_path = assembled_path
    overlays = config.get("overlays", [])
    for j, overlay in enumerate(overlays):
        overlay_path = str(WORK_DIR / f"overlay_{j}.mp4")
        add_text_overlay(
            current_path, overlay_path,
            text=overlay["text"],
            position=overlay.get("position", "bottom"),
            fontsize=overlay.get("fontsize", 48),
            fontcolor=overlay.get("fontcolor", "white"),
            bg_opacity=overlay.get("bg_opacity", 0.5),
            start_time=overlay.get("start", 0),
            end_time=overlay.get("end"),
        )
        current_path = overlay_path
    
    # Step 4: Add audio
    audio = config.get("audio")
    if audio and os.path.exists(audio.get("path", "")):
        print(f"\n🔊 Adding audio: {audio['path']}")
        audio_path = str(WORK_DIR / "with_audio.mp4")
        add_audio(
            current_path, audio["path"], audio_path,
            volume=audio.get("volume", 0.3),
            loop_audio=audio.get("loop", True),
        )
        current_path = audio_path
    
    # Step 5: Platform resize
    platform = config.get("platform")
    if platform:
        print(f"\n📐 Resizing for {platform}")
        platform_path = str(WORK_DIR / "platform.mp4")
        resize_for_platform(current_path, platform_path, platform)
        current_path = platform_path
    
    # Step 6: Copy to final output
    subprocess.run(["cp", current_path, output_path], check=True)
    size = os.path.getsize(output_path)
    duration = get_video_duration(output_path)
    
    print(f"\n✅ FINAL OUTPUT: {output_path}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
    
    return output_path


# ── Example Config ───────────────────────────────────────────────────────────

EXAMPLE_CONFIG = {
    "settings": {
        "width": 1280,
        "height": 720,
        "fps": 24,
        "crossfade_duration": 0.5
    },
    "scenes": [
        {
            "type": "title",
            "text": "The $47K Mistake",
            "duration": 3,
            "fontsize": 72,
            "fontcolor": "white",
            "bg_color": "black"
        },
        {
            "type": "video",
            "prompt": "A confident attorney in a dark suit walking through a grand courthouse hallway, cinematic lighting, slow motion, dramatic",
            "model": "kling-v2",
            "duration": 5
        },
        {
            "type": "image_to_video",
            "image_prompt": "A powerful Viking warrior in a courtroom holding a legal document, dramatic dark cinematic lighting, photorealistic",
            "motion_prompt": "slow dramatic camera push in, slight wind on cape",
            "image_model": "flux-pro",
            "model": "kling-v2",
            "duration": 5
        },
        {
            "type": "title",
            "text": "Don't be the bottleneck.",
            "duration": 2,
            "fontsize": 56,
            "bg_color": "#1a1a2e"
        }
    ],
    "overlays": [
        {
            "text": "ACT-I Legal Visionnaire",
            "position": "bottom",
            "fontsize": 36,
            "start": 3,
            "end": 12
        }
    ],
    "platform": "youtube"
}


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="fal.ai Video Assembly Pipeline")
    parser.add_argument("command", nargs="?", default="run", help="'run' or 'example'")
    parser.add_argument("--config", "-c", type=str, help="Pipeline config JSON file")
    parser.add_argument("--scenes", "-s", type=str, help="Scenes JSON file (simplified)")
    parser.add_argument("--output", "-o", type=str, default="/tmp/fal_output/assembled_video.mp4", help="Output file")
    
    args = parser.parse_args()
    
    if args.command == "example":
        print(json.dumps(EXAMPLE_CONFIG, indent=2))
        return
    
    if not os.environ.get("FAL_KEY"):
        print("ERROR: FAL_KEY not set. Add it to the repo .env")
        sys.exit(1)
    
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    elif args.scenes:
        with open(args.scenes) as f:
            scenes = json.load(f)
        config = {"scenes": scenes, "settings": {"width": 1280, "height": 720}}
    else:
        print("ERROR: Provide --config or --scenes")
        print("Run: python3 fal_assemble.py example  # to see example config")
        sys.exit(1)
    
    run_pipeline(config, args.output)


if __name__ == "__main__":
    main()
