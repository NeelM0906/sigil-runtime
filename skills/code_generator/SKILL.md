---
name: code-generator
description: Generate and save code files as artifacts
version: "1.0.0"
intent-tags: [code, script, generate, python, javascript, html]
tools-required: [write]
risk-level: low
default-enabled: true
user-invocable: false
metadata:
  sigil:
    artifact_type: code
    mime_type: text/plain
    extension: .py
inputs:
  filename:
    type: string
    required: true
    description: Output filename with extension (e.g. script.py)
  content:
    type: string
    required: true
    description: Code content to write
  language:
    type: string
    required: false
    description: Programming language (python, javascript, html, css, etc.)
outputs:
  file_path:
    type: string
    description: Path to generated code file
  file_size:
    type: integer
    description: File size in bytes
---

# Code Generator

Saves code content as artifact files. Supports any text-based code format:
- Python (.py)
- JavaScript (.js), TypeScript (.ts)
- HTML (.html), CSS (.css)
- Shell scripts (.sh)
- Configuration files (.json, .yaml, .toml)
