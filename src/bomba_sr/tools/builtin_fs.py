from __future__ import annotations

import glob
import fnmatch
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


_BINARY_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}


def _read_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    path = context.guard_path(str(arguments["path"]))
    offset = int(arguments.get("offset") or 0)
    limit = int(arguments.get("limit") or 0)

    # Binary files: extract text with lightweight parser
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        try:
            from bomba_sr.ingestion.parser import extract_text
            extracted = extract_text(str(path))
            text = extracted.get("text") or ""
            lines = text.splitlines()
            if offset < 0:
                offset = 0
            if limit > 0:
                sliced = lines[offset : offset + limit]
            else:
                sliced = lines[offset:]
            return {
                "path": str(path),
                "content": "\n".join(sliced),
                "lines": len(lines),
                "returned_lines": len(sliced),
                "format": extracted.get("format", ""),
            }
        except Exception as exc:
            return {
                "path": str(path),
                "error": f"Binary file ({path.suffix}) — extraction failed: {exc}",
                "hint": "Use the parse_document tool for document processing.",
            }

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "path": str(path),
            "error": f"Binary file — cannot read as text. Use parse_document tool for {path.suffix} files.",
        }
    lines = text.splitlines()
    if offset < 0:
        offset = 0
    if limit > 0:
        sliced = lines[offset : offset + limit]
    else:
        sliced = lines[offset:]
    return {
        "path": str(path),
        "content": "\n".join(sliced),
        "lines": len(lines),
        "returned_lines": len(sliced),
    }


def _write_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    path = context.guard_path(str(arguments["path"]))
    content = str(arguments.get("content") or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"written": True, "path": str(path), "bytes": len(content.encode("utf-8"))}


def _edit_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    path = context.guard_path(str(arguments["path"]))
    old = str(arguments.get("old_string") or "")
    new = str(arguments.get("new_string") or "")
    if not old:
        raise ValueError("old_string is required")
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError("old_string not found")
    updated = text.replace(old, new, 1)
    path.write_text(updated, encoding="utf-8")
    return {"edited": True, "path": str(path)}


def _apply_patch_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patch_text = str(arguments.get("patch") or "")
    if not patch_text.strip():
        raise ValueError("patch is required")
    patch_bin = shutil.which("patch")
    if patch_bin is None:
        raise ValueError("patch binary not found")
    proc = subprocess.run(
        [patch_bin, "-p0", "-N", "--silent"],
        input=patch_text,
        text=True,
        capture_output=True,
        cwd=str(context.workspace_root),
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"patch failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return {"applied": True}


def _glob_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    pattern = str(arguments.get("pattern") or "*")
    rel_root = str(arguments.get("path") or ".")
    root = context.guard_path(rel_root)
    glob_pattern = str(root / pattern)
    files = [p for p in glob.glob(glob_pattern, recursive=True)]
    files = [str(context.guard_path(f)) for f in files if Path(f).exists()]
    return {"files": sorted(files)}


def _literal_grep_matches(pattern: str, root: Path, file_glob: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    multiline = "\n" in pattern
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if not fnmatch.fnmatch(rel, file_glob):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if multiline:
            start = 0
            while True:
                idx = text.find(pattern, start)
                if idx < 0:
                    break
                line_no = text.count("\n", 0, idx) + 1
                snippet = " ".join(pattern.splitlines())[:240]
                matches.append({"path": str(path), "line": line_no, "snippet": snippet})
                start = idx + max(1, len(pattern))
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append({"path": str(path), "line": idx, "snippet": line.strip()})
    return matches


def _parse_document_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Parse a document (PDF, DOCX, PPTX, XLSX, HTML, images) into structured text."""
    path = context.guard_path(str(arguments["path"]))
    if not path.is_file():
        return {"error": f"File not found: {path}"}
    try:
        from bomba_sr.ingestion.parser import extract_text
        extracted = extract_text(str(path))
        return {
            "path": str(path),
            "content": extracted["text"][:30000],
            "format": extracted["format"],
            "filename": extracted["filename"],
            "byte_size": extracted["byte_size"],
        }
    except Exception as exc:
        return {"error": f"Document parsing failed: {exc}", "path": str(path)}


def _grep_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    pattern = str(arguments.get("pattern") or "").strip()
    if not pattern:
        raise ValueError("pattern is required")
    rel_root = str(arguments.get("path") or ".")
    root = context.guard_path(rel_root)
    file_glob = str(arguments.get("glob") or "**/*")

    rg_bin = shutil.which("rg")
    if rg_bin is not None and "\n" not in pattern:
        cmd = [
            rg_bin,
            "-n",
            "--hidden",
            "--fixed-strings",
            "--glob",
            file_glob,
            pattern,
            str(root),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if proc.returncode not in (0, 1):
            raise ValueError(proc.stderr.strip() or "rg failed")
        matches: list[dict[str, Any]] = []
        for line in proc.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            file_path, line_no, snippet = parts
            matches.append(
                {
                    "path": str(context.guard_path(file_path)),
                    "line": int(line_no),
                    "snippet": snippet.strip(),
                }
            )
        return {"matches": matches}

    return {"matches": _literal_grep_matches(pattern, root, file_glob)}


def builtin_fs_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="read",
            description="Read file contents.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_read_tool,
            aliases=("read_file",),
        ),
        ToolDefinition(
            name="write",
            description="Write file contents.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_write_tool,
            aliases=("write_file",),
        ),
        ToolDefinition(
            name="edit",
            description="Replace a single string occurrence in a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_edit_tool,
            aliases=("edit_file",),
        ),
        ToolDefinition(
            name="apply_patch",
            description="Apply unified diff patch.",
            parameters={
                "type": "object",
                "properties": {"patch": {"type": "string"}},
                "required": ["patch"],
                "additionalProperties": False,
            },
            risk_level="medium",
            action_type="write",
            execute=_apply_patch_tool,
        ),
        ToolDefinition(
            name="glob",
            description="Find files by glob pattern.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_glob_tool,
            aliases=("glob_files",),
        ),
        ToolDefinition(
            name="grep",
            description="Search file contents for a pattern.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_grep_tool,
            aliases=("grep_content",),
        ),
        ToolDefinition(
            name="parse_document",
            description=(
                "Parse a document file (PDF, DOCX, PPTX, XLSX, HTML, images) into structured "
                "markdown text with table extraction. Use this for binary documents that `read` "
                "cannot handle. Returns markdown content, table data, and metadata."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the document file"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_parse_document_tool,
        ),
    ]
