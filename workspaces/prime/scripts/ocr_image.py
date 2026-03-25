#!/usr/bin/env python3
"""Upload image to fal storage and run OCR via Florence-2."""
import os, json, base64, urllib.request, sys

FAL_KEY = os.environ["FAL_KEY"]
IMAGE_PATH = sys.argv[1]

# Step 1: Upload to fal storage
with open(IMAGE_PATH, "rb") as f:
    img_data = f.read()

req = urllib.request.Request(
    "https://fal.run/fal-ai/florence-2-large/detailed-caption",
    data=json.dumps({
        "image_url": f"data:image/jpeg;base64,{base64.b64encode(img_data).decode()}"
    }).encode(),
    headers={
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }
)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode())
    print("=== FLORENCE RESULT ===")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Florence failed: {e}")

# Step 2: Try OCR endpoint
req2 = urllib.request.Request(
    "https://fal.run/fal-ai/florence-2-large/ocr",
    data=json.dumps({
        "image_url": f"data:image/jpeg;base64,{base64.b64encode(img_data).decode()}"
    }).encode(),
    headers={
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }
)

try:
    resp2 = urllib.request.urlopen(req2, timeout=30)
    result2 = json.loads(resp2.read().decode())
    print("\n=== OCR RESULT ===")
    print(json.dumps(result2, indent=2))
except Exception as e:
    print(f"OCR failed: {e}")
