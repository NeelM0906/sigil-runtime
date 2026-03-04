---
name: screenshot
description: Capture screenshots of web pages using headless browser
version: "1.0.0"
intent-tags: [screenshot, browser, capture, web, image]
tools-required: [exec]
risk-level: medium
default-enabled: false
user-invocable: false
metadata:
  sigil:
    requires:
      anyBins: [chromium, google-chrome, chrome]
    artifact_type: image
    mime_type: image/png
    extension: .png
inputs:
  url:
    type: string
    required: true
    description: URL to screenshot
  width:
    type: integer
    required: false
    description: Viewport width (default 1280)
  height:
    type: integer
    required: false
    description: Viewport height (default 720)
outputs:
  file_path:
    type: string
    description: Path to screenshot PNG
  file_size:
    type: integer
    description: File size in bytes
---

# Screenshot

Captures web page screenshots using headless Chromium.
Requires a Chromium-based browser to be installed.
Falls back to a simple HTML-to-image approach if no browser is available.
