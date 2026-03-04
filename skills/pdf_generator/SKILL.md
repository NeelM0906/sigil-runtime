---
name: pdf-generator
description: Generate PDF documents from structured content
version: "1.0.0"
intent-tags: [pdf, document, report, generate, export]
tools-required: [write]
risk-level: low
default-enabled: true
user-invocable: false
metadata:
  sigil:
    requires:
      bins: [python3]
    artifact_type: pdf
    mime_type: application/pdf
    extension: .pdf
inputs:
  title:
    type: string
    required: true
    description: Document title
  content:
    type: string
    required: true
    description: Document body text (plain text or markdown-style)
  author:
    type: string
    required: false
    description: Author name
outputs:
  file_path:
    type: string
    description: Path to generated PDF file
  file_size:
    type: integer
    description: File size in bytes
---

# PDF Generator

Generates PDF documents using fpdf2. Supports:
- Title page with document title and author
- Multi-paragraph body text with automatic page breaks
- Section headers (lines starting with # or ##)
- Clean typography with DejaVu-compatible Unicode support
