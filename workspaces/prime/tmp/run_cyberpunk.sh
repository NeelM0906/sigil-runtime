#!/bin/bash
cd /Users/studio2/Projects/sigil-runtime/workspaces/prime/skills/fal-ai
eval "$(grep '^FAL_KEY=' /Users/studio2/Projects/sigil-runtime/workspaces/prime/tools/setup-seven-levers.sh)"
export FAL_KEY

PROMPT="Aerial drone shot sweeping over a cyberpunk city at night. Neon signs glow pink and blue. Rain-soaked streets reflect vivid neon light. Camera glides forward with slow banking turn revealing skyscrapers with holographic ads. Photorealistic cinematic lighting volumetric fog."

python3 fal_generate.py video --prompt "$PROMPT" --model kling-v2 --duration 5
