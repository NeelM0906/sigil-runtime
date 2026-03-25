---
name: docx_generator
description: Generate Word documents from structured content. Requires python3 with python-docx.
user-invocable: false
disable-model-invocation: false
risk-level: low
---
# DOCX Generator

Generate Word (.docx) documents from structured content using python-docx.

## Preconditions
- `python3` must be available
- `python-docx` package installed (`pip install python-docx`)

## Steps
1. Accept structured content (title, sections, tables, etc.)
2. Generate a Python script that creates the DOCX using python-docx
3. Execute the script with `exec`
4. Return the output file path
