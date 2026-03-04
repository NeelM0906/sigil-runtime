---
name: docx-generator
description: Generate Word documents from structured content
version: "1.0.0"
intent-tags: [docx, word, document, report, generate, export]
tools-required: [write]
risk-level: low
default-enabled: true
user-invocable: false
metadata:
  sigil:
    requires:
      bins: [python3]
    artifact_type: docx
    mime_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
    extension: .docx
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
    description: Path to generated DOCX file
  file_size:
    type: integer
    description: File size in bytes
---

# DOCX Generator

Generates Word (.docx) documents using python-docx. Supports:
- Document title as Heading 0
- Section headers (# and ##)
- Body paragraphs with proper spacing
- Document properties (title, author)
