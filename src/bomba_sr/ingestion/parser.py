"""Lightweight document extraction — no heavy ML dependencies."""
from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def extract_text(file_path: str | Path) -> dict:
    """Extract text from a file using lightweight methods.

    Returns:
        {
            "text": str,
            "format": str,
            "filename": str,
            "byte_size": int,
            "can_send_native": bool,
            "raw_bytes": bytes | None,
        }
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    byte_size = file_path.stat().st_size

    if ext == ".pdf":
        return _extract_pdf(file_path, byte_size)
    if ext in (".csv", ".tsv"):
        return _extract_csv(file_path, byte_size)
    if ext in (".txt", ".md", ".html"):
        return _extract_text(file_path, byte_size)
    if ext == ".docx":
        return _extract_docx(file_path, byte_size)
    if ext in (".xlsx", ".xls"):
        return _extract_xlsx(file_path, byte_size)
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return _extract_image(file_path, byte_size)

    # Fallback: try reading as text
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return {"text": text, "format": ext.lstrip("."), "filename": file_path.name,
                "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}
    except Exception:
        return {"text": f"[Binary file: {file_path.name}, {byte_size} bytes]",
                "format": ext.lstrip("."), "filename": file_path.name,
                "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}


def _extract_pdf(file_path: Path, byte_size: int) -> dict:
    raw_bytes = file_path.read_bytes()
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages[:50]:
            pages.append(page.extract_text() or "")
        text = "\n\n".join(pages)
    except Exception as exc:
        log.debug("pypdf extraction failed: %s", exc)
    return {
        "text": text,
        "format": "pdf",
        "filename": file_path.name,
        "byte_size": byte_size,
        "can_send_native": True,
        "raw_bytes": raw_bytes if byte_size <= 30_000_000 else None,
    }


def _extract_csv(file_path: Path, byte_size: int) -> dict:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"text": "[Empty CSV file]", "format": "csv", "filename": file_path.name,
                "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}
    headers = rows[0]
    md_lines = [
        "| " + " | ".join(h.strip() for h in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows[1:500]:
        padded = (row + [""] * len(headers))[:len(headers)]
        md_lines.append("| " + " | ".join(c.strip() for c in padded) + " |")
    summary = f"CSV: {file_path.name} ({len(rows)-1} rows, {len(headers)} columns)\n"
    summary += f"Columns: {', '.join(headers)}\n\n"
    summary += "\n".join(md_lines)
    return {"text": summary, "format": "csv", "filename": file_path.name,
            "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}


def _extract_text(file_path: Path, byte_size: int) -> dict:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return {"text": text, "format": file_path.suffix.lstrip("."), "filename": file_path.name,
            "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}


def _extract_docx(file_path: Path, byte_size: int) -> dict:
    try:
        from docx import Document
        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
    except Exception as exc:
        log.warning("DOCX extraction failed: %s", exc)
        text = f"[Could not extract DOCX: {exc}]"
    return {"text": text, "format": "docx", "filename": file_path.name,
            "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}


def _extract_xlsx(file_path: Path, byte_size: int) -> dict:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(file_path), read_only=True, data_only=True)
        sheets = []
        for ws in wb.worksheets[:10]:
            rows = []
            for row in ws.iter_rows(max_row=500, values_only=True):
                rows.append([str(c) if c is not None else "" for c in row])
            if rows:
                headers = rows[0]
                md = [
                    f"\n## Sheet: {ws.title}",
                    "| " + " | ".join(headers) + " |",
                    "| " + " | ".join(["---"] * len(headers)) + " |",
                ]
                for r in rows[1:]:
                    padded = (r + [""] * len(headers))[:len(headers)]
                    md.append("| " + " | ".join(padded) + " |")
                sheets.append("\n".join(md))
        text = "\n".join(sheets) if sheets else "[Empty workbook]"
        wb.close()
    except Exception as exc:
        log.warning("XLSX extraction failed: %s", exc)
        text = f"[Could not extract XLSX: {exc}]"
    return {"text": text, "format": "xlsx", "filename": file_path.name,
            "byte_size": byte_size, "can_send_native": False, "raw_bytes": None}


def _extract_image(file_path: Path, byte_size: int) -> dict:
    raw = file_path.read_bytes()
    return {
        "text": f"[Image: {file_path.name}]",
        "format": file_path.suffix.lstrip("."),
        "filename": file_path.name,
        "byte_size": byte_size,
        "can_send_native": True,
        "raw_bytes": raw if byte_size <= 20_000_000 else None,
    }


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """Chunk text for embedding storage."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append(current.strip())
            current = current[-overlap:] + "\n\n" + para
        else:
            current = (current + "\n\n" + para) if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks
