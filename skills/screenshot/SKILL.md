---
name: screenshot
description: Capture screenshots of web pages using headless browser. Requires Chromium or Chrome.
user-invocable: false
disable-model-invocation: false
risk-level: medium
---
# Screenshot Capture

Capture screenshots of web pages using a headless browser.

## Preconditions
- Chromium, Google Chrome, or Chrome must be installed.

## Steps
1. Accept a URL and optional viewport dimensions.
2. Use `browser_screenshot` tool or `exec` with headless Chrome to capture the page.
3. Save the PNG to the workspace.
4. Return the file path.
