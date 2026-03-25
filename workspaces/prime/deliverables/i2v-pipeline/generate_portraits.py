#!/usr/bin/env python3
"""
STEP 1: Generate Flux Pro v1.1 character portraits for the Hero's Journey.
Each character gets a front-facing square portrait for use as Kling i2v Element.

Usage:
  python3 generate_portraits.py              # Generate all 16
  python3 generate_portraits.py --char LION   # Generate one
  python3 generate_portraits.py --list        # List characters
"""

import fal_client, os, json, time, urllib.request, argparse

os.environ['FAL_KEY'] = os.getenv('FAL_KEY', '19a13d73-8bdd-4a83-979c-cd697297955f:c76b3d154f8ae52c01944bb2c8012771')

BASE = os.path.dirname(os.path.abspath(__file__))
PORTRAITS_DIR = os.path.join(BASE, "portraits")
REGISTRY_FILE = os.path.join(BASE, "character_registry.json")

# Style anchor — EVERY portrait uses this
STYLE = "Disney Pixar 3D cartoon animation style. Bright saturated colors. Expressive cartoon animal face. Square portrait, centered, facing camera. Clean solid background. NOT a human. NEVER a human face."

# ═══════════════════════════════════════════════════════
# CHARACTER DEFINITIONS
# Exact match to character-bible.md + generation scripts
# ═══════════════════════════════════════════════════════
CHARACTERS = {
    "LION": {
        "name": "Sean Callagy",
        "animal": "Lion",
        "prompt": f"Portrait of a powerful cartoon LION with a full golden mane, wearing dark sunglasses even indoors, teal 'Unblinded' jersey. Strong jaw. Carries himself like a king. He is a LION not a human. {STYLE}",
    },
    "BEAR": {
        "name": "Adam Gugino",
        "animal": "Bear",
        "prompt": f"Portrait of a large warm cartoon brown BEAR with kind gentle eyes, always slightly smiling. Teal jersey with sleeves rolled up. Calm and steady. He is a BEAR not a human. {STYLE}",
    },
    "FOX": {
        "name": "Fernando Valencia",
        "animal": "Fox",
        "prompt": f"Portrait of a sleek handsome cartoon FOX with perfect hair, wearing a teal jersey and red leather jacket. Charismatic speaker energy. He is a FOX not a human. {STYLE}",
    },
    "TORT": {
        "name": "Tom LaGreca",
        "animal": "Tortoise",
        "prompt": f"Portrait of an old wise cartoon TORTOISE with a cigar permanently in mouth, reading glasses perched on nose. Gray-green shell with battle scars. He is a TORTOISE not a human. {STYLE}",
    },
    "DEER": {
        "name": "Mark Winters",
        "animal": "Deer",
        "prompt": f"Portrait of a lean watchful cartoon DEER with alert ears always up, cautious eyes, teal jersey. Arms crossed. He is a DEER not a human. {STYLE}",
    },
    "OCTO": {
        "name": "Michael Smiken",
        "animal": "Octopus",
        "prompt": f"Portrait of a purple cartoon OCTOPUS with multiple arms doing different things — typing, filing, holding a phone. Orange shorts. Genius energy. He is an OCTOPUS not a human. {STYLE}",
    },
    "FAIRY": {
        "name": "Aiko",
        "animal": "Fairy",
        "prompt": f"Portrait of a small glowing golden FAIRY with holographic tech-wings (sleek, translucent, circuit patterns, NOT butterfly wings). Black hair flowing with magical energy. Surrounded by sparkle particles. Tiny but fierce. She is a FAIRY not a human. {STYLE}",
    },
    "TINK": {
        "name": "Nicole Maiello (Tink)",
        "animal": "Fairy",
        "prompt": f"Portrait of a warm sparkly FAIRY with traditional pixie dust wings, softer gentle glow. Supportive warm expression. Pixie dust trailing. She is a FAIRY not a human. {STYLE}",
    },
    "FLAM": {
        "name": "Bella Verita",
        "animal": "Flamingo",
        "prompt": f"Portrait of a tall elegant cartoon pink FLAMINGO in designer sneakers, perfect posture, expressive eyes. Diva meets warrior energy. She is a FLAMINGO not a human. {STYLE}",
    },
    "SQRL": {
        "name": "Gina Ritchie",
        "animal": "Squirrel",
        "prompt": f"Portrait of a hyperactive cartoon SQUIRREL with huge expressive eyes, tail always twitching with energy, teal jersey. Vibrating with enthusiasm. She is a SQUIRREL not a human. {STYLE}",
    },
    "FROG": {
        "name": "Dustin Empley",
        "animal": "Frog",
        "prompt": f"Portrait of a calm brilliant cartoon FROG with round glasses, thoughtful expression. Quiet genius energy. He is a FROG not a human. {STYLE}",
    },
    "OTTER": {
        "name": "Mike Vesuvio",
        "animal": "Otter",
        "prompt": f"Portrait of a sleek cartoon sea OTTER always on the phone. Italian consigliere energy. Multiple phones. He is an OTTER not a human. {STYLE}",
    },
    "EAGLE": {
        "name": "Michael Johnson",
        "animal": "Eagle",
        "prompt": f"Portrait of a big bold cartoon bald EAGLE with sharp eyes, teal jersey. Carries himself like he knows everything. Always filming. He is an EAGLE not a human. {STYLE}",
    },
    "DOVE": {
        "name": "Martha",
        "animal": "Dove",
        "prompt": f"Portrait of a graceful cartoon DOVE with warm expression. Fernando's fiancée. Peaceful, funny, observing. She is a DOVE not a human. {STYLE}",
    },
    "SNAKE": {
        "name": "Office Manager",
        "animal": "Snake",
        "prompt": f"Portrait of a thin smiling cartoon SNAKE in business casual, forked tongue testing the air. Looks helpful but carries poison. She is a SNAKE not a human. {STYLE}",
    },
    "OWL": {
        "name": "Carol Kern",
        "animal": "Owl",
        "prompt": f"Portrait of a smaller nervous cartoon OWL with reading glasses and a calculator in her talons. Head of finance. Perpetually concerned. She is an OWL not a human. {STYLE}",
    },
}


def generate_portrait(char_key: str) -> dict:
    """Generate a single Flux portrait and return the result."""
    char = CHARACTERS[char_key]
    print(f"  🎨 Generating {char_key} ({char['name']} — {char['animal']})...", flush=True)
    
    handle = fal_client.submit("fal-ai/flux-pro/v1.1", arguments={
        "prompt": char["prompt"],
        "image_size": "square_hd",  # 1024x1024
        "num_images": 1,
        "safety_tolerance": "5",
    })
    
    # Poll for result
    while True:
        status = fal_client.status("fal-ai/flux-pro/v1.1", handle.request_id, with_logs=False)
        if type(status).__name__ == "Completed":
            result = fal_client.result("fal-ai/flux-pro/v1.1", handle.request_id)
            break
        time.sleep(3)
    
    # Download portrait
    images = result.get("images", [])
    if not images:
        print(f"  ❌ No image returned for {char_key}", flush=True)
        return None
    
    url = images[0].get("url")
    if not url:
        print(f"  ❌ No URL for {char_key}", flush=True)
        return None
    
    # Save locally
    os.makedirs(PORTRAITS_DIR, exist_ok=True)
    local_path = os.path.join(PORTRAITS_DIR, f"{char_key.lower()}_portrait.png")
    urllib.request.urlretrieve(url, local_path)
    
    print(f"  ✅ {char_key} → {local_path}", flush=True)
    
    return {
        "key": char_key,
        "name": char["name"],
        "animal": char["animal"],
        "fal_url": url,
        "local_path": local_path,
    }


def load_registry() -> dict:
    """Load existing registry or create empty."""
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {}


def save_registry(registry: dict):
    """Save registry to JSON."""
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"\n📋 Registry saved: {REGISTRY_FILE}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Generate character portraits for Hero's Journey")
    parser.add_argument("--char", type=str, help="Generate single character (e.g., LION)")
    parser.add_argument("--list", action="store_true", help="List all characters")
    args = parser.parse_args()
    
    if args.list:
        print("🎭 Character Registry:")
        for k, v in CHARACTERS.items():
            print(f"  {k:8s} — {v['name']:25s} ({v['animal']})")
        return
    
    registry = load_registry()
    
    if args.char:
        char_key = args.char.upper()
        if char_key not in CHARACTERS:
            print(f"❌ Unknown character: {char_key}")
            print(f"   Valid: {', '.join(CHARACTERS.keys())}")
            return
        result = generate_portrait(char_key)
        if result:
            registry[char_key] = result
            save_registry(registry)
    else:
        print(f"🎨 Generating {len(CHARACTERS)} character portraits...\n", flush=True)
        for char_key in CHARACTERS:
            if char_key in registry and os.path.exists(registry[char_key].get("local_path", "")):
                print(f"  ⏭️  {char_key} already exists, skipping", flush=True)
                continue
            result = generate_portrait(char_key)
            if result:
                registry[char_key] = result
            time.sleep(1)  # Rate limiting
        save_registry(registry)
    
    print(f"\n🏁 Done! {len(registry)} portraits in registry.", flush=True)


if __name__ == "__main__":
    main()
