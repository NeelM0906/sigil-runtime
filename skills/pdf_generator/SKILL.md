---
name: pdf_generator
description: Generate PDF documents from structured content. Requires python3 with reportlab or weasyprint.
user-invocable: false
disable-model-invocation: false
risk-level: low
---
# PDF Generator

Generate PDF documents from structured content.

## Preconditions
- `python3` must be available
- PDF library installed (reportlab, weasyprint, or fpdf2)

## Steps
1. Accept structured content (title, sections, tables, images)
2. Generate a Python script that creates the PDF
3. Execute the script with `exec`
4. Return the output file path
