"""Collapsible tool output rendering for the BOMBA SR CLI.

Renders agentic loop tool call results as compact, collapsed blocks with
optional interactive expansion via Ctrl+O / alternate screen viewer.
"""
from __future__ import annotations

import atexit
import json
import os
import select
import shutil
import sys
import termios
import tty
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Configuration from env
# ---------------------------------------------------------------------------

PREVIEW_LIMIT: int = int(os.environ.get("BOMBA_CLI_TOOL_PREVIEW_LINES", "5"))
EXPAND_TIMEOUT: float = float(os.environ.get("BOMBA_CLI_EXPAND_TIMEOUT", "1.5"))

# ---------------------------------------------------------------------------
# ANSI Theme
# ---------------------------------------------------------------------------


def _is_color_terminal() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.environ.get("BOMBA_CLI_NO_COLOR"):
        return False
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    return True


class Theme:
    __slots__ = ("BOLD", "DIM", "RESET", "CYAN", "GREEN", "RED", "YELLOW", "REVERSE")

    def __init__(self, color: bool = True) -> None:
        if color:
            self.BOLD = "\033[1m"
            self.DIM = "\033[2m"
            self.RESET = "\033[0m"
            self.CYAN = "\033[36m"
            self.GREEN = "\033[32m"
            self.RED = "\033[31m"
            self.YELLOW = "\033[33m"
            self.REVERSE = "\033[7m"
        else:
            self.BOLD = self.DIM = self.RESET = ""
            self.CYAN = self.GREEN = self.RED = self.YELLOW = self.REVERSE = ""


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass
class CollapsedBlock:
    index: int
    tool_name: str
    tool_call_id: str
    status: str
    duration_ms: int
    risk_class: str
    summary_line: str
    preview_lines: list[str]
    total_items: int
    full_lines: list[str]
    raw_output: dict[str, Any]


@dataclass
class CollapsedTurnState:
    blocks: list[CollapsedBlock]
    assistant_text: str

    @property
    def has_collapsed_blocks(self) -> bool:
        return any(b.total_items > len(b.preview_lines) for b in self.blocks)


# ---------------------------------------------------------------------------
# Tool-Specific Formatters
#
# Each returns (summary_line, preview_lines, full_lines, total_items).
# ---------------------------------------------------------------------------

_FormatResult = tuple[str, list[str], list[str], int]


def _format_glob(output: dict[str, Any]) -> _FormatResult:
    files = output.get("files", [])
    total = len(files)
    summary = f"glob: {total} file(s)"
    full = [f"    {f}" for f in files]
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


def _format_grep(output: dict[str, Any]) -> _FormatResult:
    matches = output.get("matches", [])
    total = len(matches)
    summary = f"grep: {total} match(es)"
    full = [f"    {m.get('path', '?')}:{m.get('line', '?')}: {m.get('snippet', '')}" for m in matches]
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


def _format_code_search(output: dict[str, Any]) -> _FormatResult:
    results = output.get("results", [])
    total = len(results)
    avg_conf = output.get("avg_confidence", 0.0)
    summary = f"code_search: {total} result(s), avg confidence {avg_conf:.2f}"
    full = [
        f"    {r.get('path', '?')}:{r.get('line_start', '?')} (conf={r.get('confidence', 0):.2f})"
        for r in results
    ]
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


def _format_read(output: dict[str, Any]) -> _FormatResult:
    path = output.get("path", "?")
    lines = output.get("lines", 0)
    returned = output.get("returned_lines", lines)
    summary = f"read: {path} ({returned}/{lines} lines)"
    return summary, [], [], 0


def _format_write(output: dict[str, Any]) -> _FormatResult:
    path = output.get("path", "?")
    nbytes = output.get("bytes", 0)
    summary = f"write: {path} ({nbytes} bytes)"
    return summary, [], [], 0


def _format_edit(output: dict[str, Any]) -> _FormatResult:
    path = output.get("path", "?")
    summary = f"edit: {path}"
    return summary, [], [], 0


def _format_exec(output: dict[str, Any]) -> _FormatResult:
    cmd = output.get("command", "?")
    exit_code = output.get("exit_code", "?")
    cmd_display = cmd[:60] + "..." if len(cmd) > 60 else cmd
    summary = f"exec: `{cmd_display}` -> exit {exit_code}"
    stdout_lines = (output.get("stdout") or "").splitlines()
    stderr_lines = (output.get("stderr") or "").splitlines()
    full: list[str] = []
    if stdout_lines:
        full.append("    --- stdout ---")
        full.extend(f"    {line}" for line in stdout_lines)
    if stderr_lines:
        full.append("    --- stderr ---")
        full.extend(f"    {line}" for line in stderr_lines)
    total = len(stdout_lines) + len(stderr_lines)
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


def _format_web_search(output: dict[str, Any]) -> _FormatResult:
    results = output.get("results", [])
    total = len(results)
    query = output.get("query", "?")
    summary = f'web_search: "{query}" -> {total} result(s)'
    full = [f"    {r.get('title', '')} - {r.get('url', '')}" for r in results]
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


def _format_web_fetch(output: dict[str, Any]) -> _FormatResult:
    url = output.get("url", "?")
    content_len = len(output.get("content", ""))
    truncated = output.get("truncated", False)
    summary = f"web_fetch: {url} ({content_len} chars, truncated={truncated})"
    return summary, [], [], 0


def _format_generic(tool_name: str, output: dict[str, Any]) -> _FormatResult:
    raw = json.dumps(output, indent=2, ensure_ascii=False)
    lines = raw.splitlines()
    total = len(lines)
    summary = f"{tool_name}: {total} line(s) of output"
    full = [f"    {line}" for line in lines]
    preview = full[:PREVIEW_LIMIT]
    return summary, preview, full, total


_FORMATTERS: dict[str, Any] = {
    "glob": _format_glob,
    "grep": _format_grep,
    "code_search": _format_code_search,
    "read": _format_read,
    "write": _format_write,
    "edit": _format_edit,
    "exec": _format_exec,
    "web_search": _format_web_search,
    "web_fetch": _format_web_fetch,
}


def _format_tool_call(tc: dict[str, Any], index: int) -> CollapsedBlock:
    tool_name = tc.get("tool_name", "unknown")
    output = tc.get("output", {})
    status = tc.get("status", "unknown")

    formatter = _FORMATTERS.get(tool_name)
    if formatter:
        summary, preview, full, total = formatter(output)
    else:
        summary, preview, full, total = _format_generic(tool_name, output)

    return CollapsedBlock(
        index=index,
        tool_name=tool_name,
        tool_call_id=tc.get("tool_call_id", ""),
        status=status,
        duration_ms=tc.get("duration_ms", 0),
        risk_class=tc.get("risk_class", "unknown"),
        summary_line=summary,
        preview_lines=preview,
        total_items=total,
        full_lines=full,
        raw_output=output,
    )


# ---------------------------------------------------------------------------
# Build + Render (collapsed, inline)
# ---------------------------------------------------------------------------


def build_collapsed_state(result: dict[str, Any]) -> CollapsedTurnState:
    assistant = result.get("assistant", {})
    tool_calls = assistant.get("tool_calls") or []
    text = assistant.get("text", "")
    blocks = [_format_tool_call(tc, i) for i, tc in enumerate(tool_calls)]
    return CollapsedTurnState(blocks=blocks, assistant_text=text)


def render_collapsed(state: CollapsedTurnState, file: Any = None) -> None:
    out = file or sys.stdout
    theme = Theme(color=_is_color_terminal())

    if state.blocks:
        for block in state.blocks:
            status_color = {
                "executed": theme.GREEN,
                "error": theme.RED,
                "denied": theme.RED,
                "approval_required": theme.YELLOW,
            }.get(block.status, theme.DIM)

            header = (
                f"  {theme.DIM}[{theme.CYAN}{block.tool_name}{theme.RESET}"
                f"{theme.DIM}] {status_color}{block.status}{theme.RESET}"
                f"{theme.DIM} ({block.duration_ms}ms){theme.RESET}"
            )
            print(header, file=out)
            print(f"  {theme.BOLD}{block.summary_line}{theme.RESET}", file=out)

            for line in block.preview_lines:
                print(f"{theme.DIM}{line}{theme.RESET}", file=out)

            remaining = block.total_items - len(block.preview_lines)
            if remaining > 0:
                print(f"{theme.DIM}    ... +{remaining} more{theme.RESET}", file=out)
            print(file=out)

    print(f"sigil> {state.assistant_text}", file=out)


# ---------------------------------------------------------------------------
# Interactive Expansion Viewer
# ---------------------------------------------------------------------------

_saved_terminal_settings: list[Any] = []


def _atexit_restore_terminal() -> None:
    """Safety net: restore terminal on unexpected exit."""
    if _saved_terminal_settings:
        try:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, _saved_terminal_settings[0])
            sys.stdout.write("\033[?1049l")
            sys.stdout.flush()
        except Exception:
            pass


atexit.register(_atexit_restore_terminal)


def check_and_maybe_expand(state: CollapsedTurnState, timeout: float | None = None) -> None:
    if not state.has_collapsed_blocks:
        return
    if not sys.stdout.isatty():
        return

    effective_timeout = timeout if timeout is not None else EXPAND_TIMEOUT
    theme = Theme(color=_is_color_terminal())
    print(f"{theme.DIM}  [Ctrl+O to expand tool output]{theme.RESET}")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], effective_timeout)
        if rlist:
            ch = sys.stdin.read(1)
            if ch == "\x0f":  # Ctrl+O
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                _interactive_expand(state)
                return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _interactive_expand(state: CollapsedTurnState) -> None:
    if not sys.stdout.isatty():
        return

    theme = Theme(color=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    _saved_terminal_settings.clear()
    _saved_terminal_settings.append(old_settings)

    sys.stdout.write("\033[?1049h")
    sys.stdout.flush()

    selected_block = 0
    scroll_offset = 0

    try:
        tty.setcbreak(fd)
        while True:
            _draw_expand_view(state, theme, selected_block, scroll_offset)
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                if rlist:
                    seq = sys.stdin.read(1)
                    if seq == "[":
                        arrow = sys.stdin.read(1)
                        if arrow == "A":  # Up
                            selected_block = max(0, selected_block - 1)
                            scroll_offset = 0
                        elif arrow == "B":  # Down
                            selected_block = min(len(state.blocks) - 1, selected_block + 1)
                            scroll_offset = 0
                        elif arrow == "C":  # Right — page down
                            term_h = shutil.get_terminal_size().lines - 6
                            block = state.blocks[selected_block]
                            max_scroll = max(0, len(block.full_lines) - term_h)
                            scroll_offset = min(scroll_offset + term_h, max_scroll)
                        elif arrow == "D":  # Left — page up
                            term_h = shutil.get_terminal_size().lines - 6
                            scroll_offset = max(0, scroll_offset - term_h)
                else:
                    break  # Bare Esc — exit

            elif ch in ("q", "Q"):
                break

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
        _saved_terminal_settings.clear()


def _draw_expand_view(
    state: CollapsedTurnState,
    theme: Theme,
    selected: int,
    scroll_offset: int,
) -> None:
    cols, rows = shutil.get_terminal_size()

    sys.stdout.write("\033[2J\033[H")

    header = " TOOL OUTPUT VIEWER  |  Up/Down: select  |  Left/Right: scroll  |  Esc/q: close "
    padded = header[:cols].ljust(cols)
    print(f"{theme.REVERSE}{padded}{theme.RESET}")
    print()

    for i, block in enumerate(state.blocks):
        marker = ">" if i == selected else " "
        status_ch = {"executed": "+", "error": "!", "denied": "X", "approval_required": "?"}.get(
            block.status, " "
        )
        line = f" {marker} [{status_ch}] {block.tool_name}: {block.summary_line}"
        if i == selected:
            print(f"{theme.REVERSE}{line:{cols}}{theme.RESET}")
        else:
            print(f"{theme.DIM}{line}{theme.RESET}")

    print()
    separator = "=" * min(cols, 80)
    print(f"{theme.DIM}{separator}{theme.RESET}")
    print()

    if 0 <= selected < len(state.blocks):
        block = state.blocks[selected]
        content_lines = block.full_lines
        available_rows = max(1, rows - len(state.blocks) - 8)
        visible = content_lines[scroll_offset : scroll_offset + available_rows]

        for line in visible:
            if len(line) > cols - 2:
                line = line[: cols - 5] + "..."
            print(f"  {line}")

        if scroll_offset + available_rows < len(content_lines):
            remaining = len(content_lines) - scroll_offset - available_rows
            print(f"\n{theme.DIM}  ... {remaining} more lines (Right arrow to scroll){theme.RESET}")
        elif not content_lines:
            print(f"{theme.DIM}  (no detailed output){theme.RESET}")

    sys.stdout.flush()
