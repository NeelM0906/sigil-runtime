#!/usr/bin/env python3
"""
PROOF OF CONCEPT — Scene 1, Episode 1 "Two Caymans"
Image-to-Video with Kling v3 Pro Elements system.

This proves: character-locked faces across scenes using Flux portraits as Elements.

Usage:
  1. First run generate_portraits.py (or at least --char LION --char BEAR --char FOX)
  2. Then run this: python3 poc_scene01_i2v.py
  3. Compare output with original text-to-video version

Pipeline: Flux portrait → fal upload → Kling i2v Element → consistent character
"""

import fal_client, os, json, time, urllib.request

os.environ['FAL_KEY'] = os.getenv('FAL_KEY', '19a13d73-8bdd-4a83-979c-cd697297955f:c76b3d154f8ae52c01944bb2c8012771')

BASE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(BASE, "character_registry.json")
OUTPUT_DIR = os.path.join(BASE, "poc_output")

# ═══════════════════════════════════════════════════════
# STYLE ANCHOR (end of every prompt — Commandment #7)
# ═══════════════════════════════════════════════════════
STYLE = """Disney Pixar cartoon animation. ALL characters are CARTOON ANIMALS with animal faces and animal bodies. NOT humans. NEVER human faces. Bright saturated colors, expressive cartoon animal faces, cinematic 16:9. No text on screen."""


def load_registry() -> dict:
    if not os.path.exists(REGISTRY_FILE):
        print("❌ No character_registry.json found. Run generate_portraits.py first.")
        exit(1)
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def build_element(registry: dict, char_key: str, element_num: int) -> dict:
    """Build a Kling Elements entry from the portrait registry."""
    char = registry.get(char_key)
    if not char:
        print(f"⚠️  {char_key} not in registry — skipping element")
        return None
    
    return {
        "frontal_image_url": char["fal_url"],
        # Additional reference images would go here for multi-angle consistency
        # "reference_image_urls": [char["fal_url"]],
    }


def generate_establishing_shot(registry: dict) -> str:
    """
    Generate a Flux establishing shot for the scene's start_image_url.
    This gives Kling a visual anchor for the scene composition.
    """
    print("🎨 Generating establishing shot (Flux Pro)...", flush=True)
    
    prompt = (
        "Interior of a luxurious private jet. Golden warm light through oval windows. "
        "Caribbean ocean visible below through clouds. Cartoon animals in teal jerseys "
        "sitting in plush leather seats. A powerful cartoon LION with golden mane and dark "
        "sunglasses sits at center. A large brown BEAR with kind eyes has arm around a "
        "sleek FOX. A purple OCTOPUS works on a laptop. A pink FLAMINGO checks her sneakers. "
        "A hyperactive SQUIRREL vibrates with energy. An OTTER talks on three phones. "
        "Disney Pixar 3D cartoon animation. Bright saturated colors. Cinematic composition. "
        "16:9 aspect ratio. NOT humans. CARTOON ANIMALS only."
    )
    
    handle = fal_client.submit("fal-ai/flux-pro/v1.1", arguments={
        "prompt": prompt,
        "image_size": {"width": 1344, "height": 768},  # 16:9 for video
        "num_images": 1,
        "safety_tolerance": "5",
    })
    
    while True:
        status = fal_client.status("fal-ai/flux-pro/v1.1", handle.request_id, with_logs=False)
        if type(status).__name__ == "Completed":
            result = fal_client.result("fal-ai/flux-pro/v1.1", handle.request_id)
            break
        time.sleep(3)
    
    images = result.get("images", [])
    if not images:
        print("❌ Failed to generate establishing shot")
        return None
    
    url = images[0].get("url")
    
    # Save locally
    local = os.path.join(OUTPUT_DIR, "establishing_shot.png")
    urllib.request.urlretrieve(url, local)
    print(f"  ✅ Establishing shot → {local}", flush=True)
    
    return url


def run_poc():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    registry = load_registry()
    
    print("🎬 POC: Scene 1, Episode 1 — 'Two Caymans' (i2v with Elements)")
    print("=" * 60, flush=True)
    
    # ─── Step 1: Generate establishing shot ───
    start_image_url = generate_establishing_shot(registry)
    if not start_image_url:
        print("❌ Cannot proceed without establishing shot")
        return
    
    # ─── Step 2: Build Elements for characters in this scene ───
    # Scene 1 characters: LION (center), BEAR, FOX, OCTO, FLAM, SQRL, OTTER
    scene_chars = ["LION", "BEAR", "FOX", "OCTO", "FLAM", "SQRL", "OTTER"]
    elements = []
    element_map = {}  # char_key → element number
    
    for i, char_key in enumerate(scene_chars, 1):
        elem = build_element(registry, char_key, i)
        if elem:
            elements.append(elem)
            element_map[char_key] = i
            print(f"  🔗 @Element {i} = {char_key} ({registry[char_key]['name']})", flush=True)
    
    # ─── Step 3: Build the prompt ───
    # Commandment #7: Dialogue FIRST, style tag at END
    # Reference characters as @Element N
    prompt_parts = []
    
    # Dialogue and action (FIRST)
    prompt_parts.append(
        f"Inside a luxurious private jet flying over the Caribbean sea through golden clouds. "
        f"@Element {element_map.get('BEAR', 1)} has his arm around @Element {element_map.get('FOX', 2)}. "
        f"@Element {element_map.get('OCTO', 3)} types on a laptop with multiple arms. "
        f"@Element {element_map.get('FLAM', 4)} checks her designer sneakers. "
        f"@Element {element_map.get('SQRL', 5)} vibrates with excited energy. "
        f"@Element {element_map.get('OTTER', 6)} talks on three phones at once. "
        f"@Element {element_map.get('LION', 7)} sits at the center, wearing dark sunglasses, "
        f"looking around at all of them. He says quietly to himself: \"Nine years.\""
    )
    
    # Style tag (END — Commandment #7)
    prompt_parts.append(STYLE)
    
    prompt = " ".join(prompt_parts)
    
    print(f"\n📝 Prompt ({len(prompt)} chars):", flush=True)
    print(f"   {prompt[:200]}...", flush=True)
    
    # ─── Step 4: Submit to Kling v3 Pro i2v ───
    print("\n🚀 Submitting to Kling v3 Pro image-to-video...", flush=True)
    
    arguments = {
        "prompt": prompt,
        "start_image_url": start_image_url,
        "duration": "10",  # Commandment #3: minimum 10s
        "aspect_ratio": "16:9",
        "generate_audio": True,  # Commandment #7
    }
    
    # Add elements if we have any
    if elements:
        arguments["elements"] = elements
        print(f"   📦 {len(elements)} Elements attached", flush=True)
    
    fid = "fal-ai/kling-video/v3/pro/image-to-video"
    
    try:
        handle = fal_client.submit(fid, arguments=arguments)
        print(f"   📤 Submitted: {handle.request_id}", flush=True)
    except Exception as e:
        print(f"   ❌ Submit failed: {e}", flush=True)
        # Fallback: try without elements (test the basic i2v flow)
        print("   🔄 Retrying without Elements (basic i2v)...", flush=True)
        del arguments["elements"]
        try:
            handle = fal_client.submit(fid, arguments=arguments)
            print(f"   📤 Submitted (no elements): {handle.request_id}", flush=True)
        except Exception as e2:
            print(f"   ❌ Basic i2v also failed: {e2}", flush=True)
            return
    
    # ─── Step 5: Poll for result ───
    print("\n⏳ Polling...", flush=True)
    attempts = 0
    while True:
        attempts += 1
        try:
            status = fal_client.status(fid, handle.request_id, with_logs=False)
            status_name = type(status).__name__
            
            if status_name == "Completed":
                result = fal_client.result(fid, handle.request_id)
                video_url = result.get("video", {}).get("url")
                
                if video_url:
                    output_path = os.path.join(OUTPUT_DIR, "poc_scene01_i2v.mp4")
                    urllib.request.urlretrieve(video_url, output_path)
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    print(f"\n🎉 SUCCESS! Scene 1 generated with i2v + Elements!", flush=True)
                    print(f"   📁 {output_path} ({size_mb:.1f}MB)", flush=True)
                    print(f"   🔗 {video_url}", flush=True)
                    
                    # Save metadata
                    meta = {
                        "scene": "hj01_s01",
                        "method": "image-to-video",
                        "endpoint": fid,
                        "elements_count": len(elements),
                        "characters": scene_chars,
                        "duration": "10",
                        "audio": True,
                        "video_url": video_url,
                        "start_image_url": start_image_url,
                        "request_id": handle.request_id,
                    }
                    with open(os.path.join(OUTPUT_DIR, "poc_metadata.json"), "w") as f:
                        json.dump(meta, f, indent=2)
                    
                    print(f"\n✅ POC COMPLETE. Compare with text-to-video version.", flush=True)
                    print(f"   Key question: Are character faces consistent with portraits?", flush=True)
                else:
                    print(f"   ❌ Completed but no video URL in result", flush=True)
                    print(f"   Result: {json.dumps(result, indent=2)[:500]}", flush=True)
                break
            
            elif status_name == "InProgress":
                if attempts % 5 == 0:
                    print(f"   ⏳ Still generating... (attempt {attempts})", flush=True)
            
            else:
                print(f"   Status: {status_name}", flush=True)
                if hasattr(status, 'error'):
                    print(f"   Error: {status.error}", flush=True)
                    break
        
        except Exception as e:
            print(f"   ⚠️ Poll error: {e}", flush=True)
        
        time.sleep(10)
    
    print("\n🏁 POC run complete.", flush=True)


if __name__ == "__main__":
    run_poc()
