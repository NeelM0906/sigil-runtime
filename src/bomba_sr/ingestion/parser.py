"""Document parsing via Docling — PDF, DOCX, PPTX, XLSX, HTML, images."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Lazy singleton — Docling loads ~2GB of models on first use
_converter = None


def get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
        log.info("Docling DocumentConverter initialized")
    return _converter


def parse_document(file_path: str | Path) -> dict:
    """Parse any supported document and return structured output.

    Returns:
        {
            "markdown": str,
            "chunks": list[str],
            "tables": list[dict],
            "metadata": {"filename": str, "page_count": int, "format": str},
        }
    """
    file_path = Path(file_path)
    converter = get_converter()
    result = converter.convert(str(file_path))
    doc = result.document

    markdown = doc.export_to_markdown()

    chunks = _chunk_markdown(markdown, max_chunk_chars=1500, overlap_chars=200)

    tables: list[dict] = []
    for table in getattr(doc, "tables", []):
        try:
            df = table.export_to_dataframe()
            tables.append({
                "csv": df.to_csv(index=False),
                "headers": list(df.columns),
                "rows": len(df),
            })
        except Exception:
            pass

    return {
        "markdown": markdown,
        "chunks": chunks,
        "tables": tables,
        "metadata": {
            "filename": file_path.name,
            "page_count": getattr(doc, "num_pages", None) or len(getattr(doc, "pages", [])) or 0,
            "format": file_path.suffix.lstrip("."),
        },
    }


def _chunk_markdown(text: str, max_chunk_chars: int = 1500, overlap_chars: int = 200) -> list[str]:
    """Split markdown into overlapping chunks for embedding."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chunk_chars and current:
            chunks.append(current.strip())
            current = current[-overlap_chars:] + "\n\n" + para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks
