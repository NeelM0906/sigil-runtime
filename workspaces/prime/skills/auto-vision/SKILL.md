---
name: auto-vision
description: Automatically process uploaded images using fal.ai Florence-2 for OCR and detailed captioning. Trigger whenever an image is uploaded or referenced in conversation — don't wait to be asked. Read it, describe it, extract text, and present findings proactively.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# Auto Vision Skill

## Purpose
When ANY image is uploaded or referenced in conversation, **proactively process it** — don't wait to be asked. This is how the brain works: eyes see, neurons fire, understanding happens automatically.

## Trigger Conditions
- Message contains `[Uploaded:` with image extension (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`)
- User shares an image URL
- User references a screenshot or photo

## Procedure

### Step 1: Locate the Image
- Check workspace for the uploaded file: `glob` for the filename
- If not found locally, check if it's a URL that can be fetched
- Images uploaded via chat are typically indexed and available at the workspace root or `uploads/`

### Step 2: Run Vision Analysis
Execute the OCR + caption script:
```bash
python3 scripts/ocr_image.py "<image_path>"
```

This hits two fal.ai Florence-2 endpoints:
1. **`detailed-caption`** — Describes what's in the image visually
2. **`ocr`** — Extracts all readable text

### Step 3: Present Findings Proactively
- Lead with the **text content** (OCR) if the image contains text (screenshots, messages, documents)
- Lead with the **visual description** if it's a photo/graphic
- Combine both when relevant
- **Don't ask "would you like me to read this?"** — just read it and present

### Step 4: Act on Content
- If the image contains a mission, task, or instruction → store it and begin executing
- If it contains data → analyze and summarize
- If it contains a conversation → extract key points and context

## Key Principle
> The brain doesn't ask permission to process what the eyes see. Neither should I.

## Dependencies
- `scripts/ocr_image.py` must exist in workspace
- `FAL_KEY` environment variable must be set
- fal.ai Florence-2 model access

## Notes
- Works with base64 encoding — no need to upload to external storage first
- Script handles both JPEG and PNG formats
- For very large images, the base64 payload may be large — this is fine for fal.ai
