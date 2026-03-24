---
name: code_generator
description: Generate and save code files as artifacts. Supports Python, JavaScript, TypeScript, HTML, CSS, shell scripts, and configuration files.
user-invocable: false
disable-model-invocation: false
risk-level: low
---
# Code Generator

Saves code content as artifact files. Supports any text-based code format:
- Python (.py)
- JavaScript (.js), TypeScript (.ts)
- HTML (.html), CSS (.css)
- Shell scripts (.sh)
- Configuration files (.json, .yaml, .toml)

## Usage
1. Determine the target filename and extension.
2. Write the code content using the `write` tool.
3. Return the file path and size.
