from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from bomba_sr.codeintel.base import CodeIntelligenceAdapter, CodeIntelError
from bomba_sr.runtime.tenancy import TenantContext


_SYMBOL_LINE_PATTERNS = [
    re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("),
    re.compile(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    re.compile(r"^\s*function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\("),
    re.compile(r"^\s*(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*="),
]

_MAX_SYMBOL_NAME_LEN = 200
_VALID_SYMBOL_RE = re.compile(r"^[a-zA-Z0-9_./$\-: ]+$")


def _validate_symbol_name(name: str) -> str:
    """Validate that a symbol name looks like a code identifier, not freeform text."""
    if not name or not name.strip():
        raise CodeIntelError("symbol_name is required")
    name = name.strip()
    if len(name) > _MAX_SYMBOL_NAME_LEN:
        raise CodeIntelError(
            f"Invalid symbol_name — must be a code identifier (max {_MAX_SYMBOL_NAME_LEN} chars), "
            f"got {len(name)} chars. Do not pass freeform text or prompts."
        )
    if "\n" in name or "\r" in name:
        raise CodeIntelError(
            "Invalid symbol_name — must be a code identifier, not multi-line text."
        )
    if not _VALID_SYMBOL_RE.match(name):
        raise CodeIntelError(
            "Invalid symbol_name — must contain only alphanumeric characters, "
            "underscores, dots, slashes, dashes, colons, or dollar signs. "
            "Do not pass freeform text or prompts as symbol names."
        )
    return name


class NativeCodeIntelAdapter(CodeIntelligenceAdapter):
    @property
    def backend_name(self) -> str:
        return "native"

    def is_available(self) -> bool:
        return True

    def _invoke_impl(self, tenant: TenantContext, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "get_symbols_overview":
            return self._get_symbols_overview(arguments)
        if tool_name == "find_symbol":
            return self._find_symbol(tenant, arguments, references_only=False)
        if tool_name == "find_referencing_symbols":
            return self._find_symbol(tenant, arguments, references_only=True)
        if tool_name == "replace_symbol_body":
            return self._replace_range(arguments)
        if tool_name == "insert_before_symbol":
            return self._insert(arguments, before=True)
        if tool_name == "insert_after_symbol":
            return self._insert(arguments, before=False)
        if tool_name == "rename_symbol":
            return self._rename_symbol(tenant, arguments)
        raise CodeIntelError(f"Unsupported native tool: {tool_name}")

    def _get_symbols_overview(self, arguments: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(str(arguments["file_path"]))
        text = file_path.read_text(encoding="utf-8")
        symbols: list[dict[str, Any]] = []
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern in _SYMBOL_LINE_PATTERNS:
                match = pattern.search(line)
                if match is None:
                    continue
                symbols.append(
                    {
                        "name": match.group(1),
                        "line": idx,
                        "signature": line.strip(),
                        "file_path": str(file_path),
                    }
                )
                break
        return {"symbols": symbols, "file_path": str(file_path)}

    def _find_symbol(self, tenant: TenantContext, arguments: dict[str, Any], references_only: bool) -> dict[str, Any]:
        symbol = _validate_symbol_name(str(arguments.get("symbol_name") or ""))
        scope = arguments.get("scope") or ["."]
        cmd = [
            "rg",
            "-n",
            "--hidden",
            "-g",
            "!.git",
            "-g",
            "!node_modules",
            rf"\b{re.escape(symbol)}\b",
            *scope,
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(tenant.workspace_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode not in (0, 1):
            raise CodeIntelError(f"rg failed: {proc.stderr.strip()}")

        hits: list[dict[str, Any]] = []
        for line in proc.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            path, line_no_s, snippet = parts
            try:
                line_no = int(line_no_s)
            except ValueError:
                continue
            if references_only and re.search(rf"\b(?:def|class|function)\s+{re.escape(symbol)}\b", snippet):
                continue
            hits.append(
                {
                    "file_path": str(Path(path).resolve()),
                    "line": line_no,
                    "snippet": snippet.strip(),
                }
            )
        return {
            "symbol_name": symbol,
            "hits": hits,
            "command": " ".join(shlex.quote(x) for x in cmd),
        }

    def _replace_range(self, arguments: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(str(arguments["file_path"]))
        start_line = int(arguments["start_line"])
        end_line = int(arguments["end_line"])
        new_body = str(arguments["new_body"])

        if start_line < 1 or end_line < start_line:
            raise ValueError("Invalid line range for replace_symbol_body")

        lines = file_path.read_text(encoding="utf-8").splitlines()
        head = lines[: start_line - 1]
        tail = lines[end_line:]
        merged = head + new_body.splitlines() + tail
        file_path.write_text("\n".join(merged) + "\n", encoding="utf-8")

        return {
            "file_path": str(file_path),
            "start_line": start_line,
            "end_line": end_line,
            "changed": True,
        }

    def _insert(self, arguments: dict[str, Any], before: bool) -> dict[str, Any]:
        file_path = Path(str(arguments["file_path"]))
        line_no = int(arguments["line"])
        text = str(arguments["text"])
        lines = file_path.read_text(encoding="utf-8").splitlines()

        if line_no < 1:
            raise ValueError("line must be >= 1")

        idx = line_no - 1 if before else line_no
        idx = max(0, min(idx, len(lines)))
        lines[idx:idx] = text.splitlines()
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "file_path": str(file_path),
            "line": line_no,
            "inserted_before": before,
            "changed": True,
        }

    def _rename_symbol(self, tenant: TenantContext, arguments: dict[str, Any]) -> dict[str, Any]:
        old = _validate_symbol_name(str(arguments.get("old_name") or ""))
        new = _validate_symbol_name(str(arguments.get("new_name") or ""))
        if not old or not new:
            raise ValueError("old_name and new_name are required")

        target_files: list[Path] = []
        if "file_path" in arguments:
            target_files.append(Path(str(arguments["file_path"])))
        else:
            scope = arguments.get("scope") or ["."]
            cmd = ["rg", "-l", "--hidden", "-g", "!.git", "-g", "!node_modules", rf"\b{re.escape(old)}\b", *scope]
            proc = subprocess.run(
                cmd,
                cwd=str(tenant.workspace_root),
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode not in (0, 1):
                raise CodeIntelError(f"rg failed during rename: {proc.stderr.strip()}")
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                target_files.append((tenant.workspace_root / line.strip()).resolve())

        changed_files: list[str] = []
        pattern = re.compile(rf"\b{re.escape(old)}\b")
        for path in target_files:
            original = path.read_text(encoding="utf-8")
            updated, count = pattern.subn(new, original)
            if count == 0:
                continue
            path.write_text(updated, encoding="utf-8")
            changed_files.append(str(path))

        return {
            "old_name": old,
            "new_name": new,
            "changed_files": changed_files,
            "changed": bool(changed_files),
        }
