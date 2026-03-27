#!/usr/bin/env python3
"""
SIGIL Runtime — TUI Installer

Interactive terminal installer that walks through:
  1. Prerequisite checks (Python, Node, ports)
  2. Python venv creation + dependency install
  3. Frontend dependency install (optional)
  4. API key configuration (.env)
  5. Feature module selection
  6. Portable root bootstrap
  7. Optional service launch

Usage:
    python3 scripts/install_tui.py
"""

from __future__ import annotations

import curses
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ENV_FILE = REPO_ROOT / ".env"
VENV_DIR = REPO_ROOT / ".venv"
MC_DIR = REPO_ROOT / "mission-control"
BACKEND_PORT = 8787
FRONTEND_PORT = 5173

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class StepStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PrereqResult:
    name: str
    ok: bool
    version: str = ""
    detail: str = ""


@dataclass
class ApiKey:
    env_var: str
    label: str
    required: bool = False
    value: str = ""
    description: str = ""
    group: str = "core"


@dataclass
class FeatureToggle:
    env_var: str
    label: str
    description: str
    enabled: bool = False
    requires_keys: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Key & feature definitions
# ---------------------------------------------------------------------------

API_KEYS: list[ApiKey] = [
    ApiKey("OPENROUTER_API_KEY", "OpenRouter API Key", required=True,
           description="Primary LLM routing (required for live model access)",
           group="core"),
    ApiKey("ANTHROPIC_API_KEY", "Anthropic API Key",
           description="Direct Anthropic access (optional, auto-selected if set)",
           group="core"),
    ApiKey("OPENAI_API_KEY", "OpenAI API Key",
           description="OpenAI access + embeddings for semantic memory",
           group="core"),
    ApiKey("BRAVE_API_KEY", "Brave Search API Key",
           description="Web search (falls back to DuckDuckGo if unset)",
           group="web"),
    ApiKey("PINECONE_API_KEY", "Pinecone API Key",
           description="Vector database for knowledge retrieval",
           group="pinecone"),
    ApiKey("PINECONE_API_KEY_STRATA", "Pinecone STRATA Key",
           description="Secondary Pinecone account for STRATA indexes",
           group="pinecone"),
    ApiKey("BLAND_API_KEY", "Bland.ai API Key",
           description="Voice call management (outbound calls, transcripts)",
           group="voice"),
    ApiKey("ZOOM_ACCOUNT_ID", "Zoom Account ID",
           description="Zoom S2S OAuth — transcript extraction",
           group="zoom"),
    ApiKey("ZOOM_CLIENT_ID", "Zoom Client ID",
           description="Zoom S2S OAuth client",
           group="zoom"),
    ApiKey("ZOOM_CLIENT_SECRET", "Zoom Client Secret",
           description="Zoom S2S OAuth secret",
           group="zoom"),
]

FEATURES: list[FeatureToggle] = [
    FeatureToggle("BOMBA_PINECONE_ENABLED", "Pinecone Knowledge Base",
                  "Vector retrieval across 14+ indexes (155K+ vectors)",
                  requires_keys=["PINECONE_API_KEY"]),
    FeatureToggle("BOMBA_VOICE_ENABLED", "Voice Calls (Bland.ai)",
                  "Outbound calls, transcripts, pathway management",
                  requires_keys=["BLAND_API_KEY"]),
    FeatureToggle("BOMBA_COLOSSEUM_ENABLED", "Colosseum Tournaments",
                  "CHDDIA² being evaluation & evolution engine"),
    FeatureToggle("BOMBA_PROVE_AHEAD_ENABLED", "Prove-Ahead Intelligence",
                  "Competitive intelligence research tools"),
    FeatureToggle("BOMBA_TEAM_MANAGER_ENABLED", "Team Manager",
                  "Agent canvas / org chart management"),
    FeatureToggle("BOMBA_HEARTBEAT_ENABLED", "Heartbeat Daemon",
                  "Background proactive check loop (reads HEARTBEAT.md)"),
    FeatureToggle("BOMBA_CRON_ENABLED", "Cron Scheduler",
                  "Recurring task execution via cron expressions"),
]

STEPS = [
    "Prerequisites",
    "Python Environment",
    "Frontend (optional)",
    "API Keys",
    "Feature Modules",
    "Bootstrap",
    "Launch",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_cmd(cmd: list[str], cwd: Optional[Path] = None,
            timeout: int = 120) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(cwd) if cwd else None, timeout=timeout,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def check_port(port: int) -> bool:
    """Return True if port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def version_tuple(v: str) -> tuple[int, ...]:
    """Parse '3.11.2' -> (3, 11, 2)."""
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


# ---------------------------------------------------------------------------
# TUI rendering primitives
# ---------------------------------------------------------------------------

# Color pair IDs
C_NORMAL = 0
C_TITLE = 1
C_SUCCESS = 2
C_ERROR = 3
C_WARN = 4
C_ACCENT = 5
C_DIM = 6
C_INPUT = 7
C_HIGHLIGHT = 8


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(C_SUCCESS, curses.COLOR_GREEN, -1)
    curses.init_pair(C_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(C_WARN, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_ACCENT, curses.COLOR_MAGENTA, -1)
    curses.init_pair(C_DIM, curses.COLOR_WHITE, -1)
    curses.init_pair(C_INPUT, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(C_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)


def draw_box(win, y: int, x: int, h: int, w: int, title: str = ""):
    """Draw a box with optional title."""
    win.attron(curses.color_pair(C_DIM))
    # corners
    win.addch(y, x, curses.ACS_ULCORNER)
    win.addch(y, x + w - 1, curses.ACS_URCORNER)
    win.addch(y + h - 1, x, curses.ACS_LLCORNER)
    try:
        win.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
    except curses.error:
        pass
    # horizontals
    for cx in range(x + 1, x + w - 1):
        win.addch(y, cx, curses.ACS_HLINE)
        try:
            win.addch(y + h - 1, cx, curses.ACS_HLINE)
        except curses.error:
            pass
    # verticals
    for cy in range(y + 1, y + h - 1):
        win.addch(cy, x, curses.ACS_VLINE)
        try:
            win.addch(cy, x + w - 1, curses.ACS_VLINE)
        except curses.error:
            pass
    win.attroff(curses.color_pair(C_DIM))
    if title:
        t = f" {title} "
        win.addstr(y, x + 2, t, curses.color_pair(C_TITLE) | curses.A_BOLD)


def safe_addstr(win, y: int, x: int, text: str, attr=0):
    """addstr that won't crash at screen edges."""
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    avail = max_x - x - 1
    if avail <= 0:
        return
    try:
        win.addstr(y, x, text[:avail], attr)
    except curses.error:
        pass


def draw_header(win, step_idx: int):
    """Draw the persistent header with step progress."""
    max_y, max_x = win.getmaxyx()
    # Title bar
    title = " SIGIL Runtime Installer "
    pad = max_x - len(title)
    bar = title + " " * max(pad, 0)
    safe_addstr(win, 0, 0, bar[:max_x],
                curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD)

    # Step indicators
    y = 2
    safe_addstr(win, y, 2, "Steps:", curses.color_pair(C_DIM))
    x = 9
    for i, name in enumerate(STEPS):
        if i == step_idx:
            marker = ">"
            attr = curses.color_pair(C_ACCENT) | curses.A_BOLD
        elif i < step_idx:
            marker = "+"
            attr = curses.color_pair(C_SUCCESS)
        else:
            marker = "."
            attr = curses.color_pair(C_DIM)
        label = f" {marker} {name} "
        safe_addstr(win, y, x, label, attr)
        x += len(label) + 1
        if x >= max_x - 10:
            break

    # Separator
    for cx in range(max_x - 1):
        try:
            win.addch(3, cx, curses.ACS_HLINE, curses.color_pair(C_DIM))
        except curses.error:
            pass


def draw_footer(win, text: str):
    max_y, max_x = win.getmaxyx()
    for cx in range(max_x - 1):
        try:
            win.addch(max_y - 2, cx, curses.ACS_HLINE, curses.color_pair(C_DIM))
        except curses.error:
            pass
    safe_addstr(win, max_y - 1, 2, text[:max_x - 4], curses.color_pair(C_DIM))


def text_input(win, y: int, x: int, width: int, prompt: str = "",
               secret: bool = False, prefill: str = "") -> str:
    """Single-line text input field. Returns the entered string or empty on ESC."""
    curses.curs_set(1)
    if prompt:
        safe_addstr(win, y, x, prompt, curses.color_pair(C_DIM))
        x += len(prompt)

    buf = list(prefill)
    cursor = len(buf)
    field_w = max(width - len(prompt), 10)

    def _render():
        display = "".join(buf)
        if secret and display:
            display = "*" * len(display)
        # Pad to clear old text
        padded = display + " " * max(field_w - len(display), 0)
        safe_addstr(win, y, x, padded[:field_w],
                    curses.color_pair(C_INPUT))
        win.move(y, min(x + cursor, x + field_w - 1))

    _render()
    win.refresh()

    while True:
        ch = win.getch()
        if ch in (curses.KEY_ENTER, 10, 13):
            break
        elif ch == 27:  # ESC
            curses.curs_set(0)
            return ""
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if cursor > 0:
                buf.pop(cursor - 1)
                cursor -= 1
        elif ch == curses.KEY_DC:
            if cursor < len(buf):
                buf.pop(cursor)
        elif ch == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif ch == curses.KEY_RIGHT:
            cursor = min(len(buf), cursor + 1)
        elif ch == curses.KEY_HOME:
            cursor = 0
        elif ch == curses.KEY_END:
            cursor = len(buf)
        elif 32 <= ch <= 126:
            buf.insert(cursor, chr(ch))
            cursor += 1
        _render()
        win.refresh()

    curses.curs_set(0)
    return "".join(buf)


def confirm(win, y: int, x: int, prompt: str, default: bool = True) -> bool:
    """Yes/no prompt. Returns bool."""
    hint = "[Y/n]" if default else "[y/N]"
    safe_addstr(win, y, x, f"{prompt} {hint} ", curses.color_pair(C_DIM))
    win.refresh()
    while True:
        ch = win.getch()
        if ch in (curses.KEY_ENTER, 10, 13):
            return default
        elif ch in (ord("y"), ord("Y")):
            return True
        elif ch in (ord("n"), ord("N")):
            return False


def wait_key(win, y: int, x: int, msg: str = "Press any key to continue..."):
    safe_addstr(win, y, x, msg, curses.color_pair(C_DIM))
    win.refresh()
    win.getch()


def show_spinner(win, y: int, x: int, label: str, func, *args, **kwargs):
    """Run func in foreground while showing a spinner. Returns func result."""
    frames = ["   ", ".  ", ".. ", "..."]
    safe_addstr(win, y, x, f"  {label}...", curses.color_pair(C_WARN))
    win.refresh()

    # We can't truly async here without threads, so just call it
    result = func(*args, **kwargs)
    return result


# ---------------------------------------------------------------------------
# Installer steps
# ---------------------------------------------------------------------------


def step_prerequisites(win) -> list[PrereqResult]:
    """Check Python, Node, npm, ports."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 0)
    draw_footer(win, "Checking system prerequisites...")

    content_y = 5
    safe_addstr(win, content_y, 4, "Checking Prerequisites",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 2

    results: list[PrereqResult] = []

    checks = [
        ("Node.js 20+", ["node", "--version"], (20,)),
        ("npm", ["npm", "--version"], (1,)),
    ]

    # Python check: try multiple candidates to find a suitable one
    python_candidates = ["python3"]
    # Check if .venv python exists and is newer
    venv_python = VENV_DIR / "bin" / "python"
    if venv_python.exists():
        python_candidates.insert(0, str(venv_python))
    # Also try common versioned names
    for v in ("python3.14", "python3.13", "python3.12", "python3.11"):
        if shutil.which(v):
            python_candidates.insert(0, v)

    python_ok = False
    python_version = ""
    python_bin = ""
    for candidate in python_candidates:
        rc, out, err = run_cmd([candidate, "--version"])
        ver_match = re.search(r"(\d+\.\d+[\.\d]*)", out)
        if rc == 0 and ver_match:
            ver_str = ver_match.group(1)
            if version_tuple(ver_str) >= (3, 11):
                python_ok = True
                python_version = ver_str
                python_bin = candidate
                break

    if not python_ok:
        # Fall back to whatever python3 reports
        rc, out, _ = run_cmd(["python3", "--version"])
        ver_match = re.search(r"(\d+\.\d+[\.\d]*)", out)
        python_version = ver_match.group(1) if ver_match else "not found"

    r = PrereqResult("Python 3.11+", python_ok, python_version,
                     "" if python_ok else f"system python3 is {python_version}")
    results.append(r)
    icon = "+" if python_ok else "x"
    color = C_SUCCESS if python_ok else C_ERROR
    if python_ok:
        src = f" ({python_bin})" if python_bin != "python3" else ""
        detail = f"v{python_version}{src}"
    else:
        detail = f"v{python_version} (need 3.11+)"
    safe_addstr(win, content_y, 6,
                f"  [{icon}] Python 3.11+: {detail}              ",
                curses.color_pair(color))
    content_y += 1
    win.refresh()

    for label, cmd, min_ver in checks:
        safe_addstr(win, content_y, 6, f"Checking {label}...",
                    curses.color_pair(C_DIM))
        win.refresh()
        rc, out, err = run_cmd(cmd)
        version_str = out.replace("v", "").strip()
        # Extract version from output like "Python 3.14.0"
        ver_match = re.search(r"(\d+\.\d+[\.\d]*)", out)
        if ver_match:
            version_str = ver_match.group(1)

        ok = False
        if rc == 0 and ver_match:
            ok = version_tuple(version_str) >= min_ver

        r = PrereqResult(label, ok, version_str,
                         err if not ok else "")
        results.append(r)

        icon = "+" if ok else "x"
        color = C_SUCCESS if ok else C_ERROR
        detail = f"v{version_str}" if ok else (r.detail or "not found")
        safe_addstr(win, content_y, 6,
                    f"  [{icon}] {label}: {detail}              ",
                    curses.color_pair(color))
        content_y += 1
        win.refresh()

    # Port checks
    for port, name in [(BACKEND_PORT, "Backend"), (FRONTEND_PORT, "Frontend")]:
        avail = check_port(port)
        r = PrereqResult(f"Port {port} ({name})", avail,
                         detail="" if avail else "in use")
        results.append(r)
        icon = "+" if avail else "!"
        color = C_SUCCESS if avail else C_WARN
        detail = "available" if avail else "in use (will need to free it)"
        safe_addstr(win, content_y, 6,
                    f"  [{icon}] Port {port} ({name}): {detail}",
                    curses.color_pair(color))
        content_y += 1
        win.refresh()

    # Summary
    content_y += 1
    critical = [r for r in results if not r.ok and "Port" not in r.name]
    if critical:
        safe_addstr(win, content_y, 6,
                    "Missing critical prerequisites. Install them before continuing.",
                    curses.color_pair(C_ERROR) | curses.A_BOLD)
        content_y += 1
        for r in critical:
            safe_addstr(win, content_y, 8, f"- {r.name}: {r.detail}",
                        curses.color_pair(C_ERROR))
            content_y += 1
        content_y += 1
        wait_key(win, content_y, 6, "Press any key to exit...")
        return []
    else:
        safe_addstr(win, content_y, 6,
                    "All prerequisites met!",
                    curses.color_pair(C_SUCCESS) | curses.A_BOLD)

    content_y += 2
    wait_key(win, content_y, 6)
    return results


def step_python_env(win) -> bool:
    """Create venv and install deps."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 1)

    content_y = 5
    safe_addstr(win, content_y, 4, "Python Environment Setup",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 2

    venv_exists = VENV_DIR.exists() and (VENV_DIR / "bin" / "python").exists()
    if venv_exists:
        safe_addstr(win, content_y, 6,
                    f"Existing venv found at .venv/",
                    curses.color_pair(C_SUCCESS))
        content_y += 1
        reuse = confirm(win, content_y, 6, "Reuse existing venv?", default=True)
        content_y += 1
        if not reuse:
            safe_addstr(win, content_y, 6, "Removing old venv...",
                        curses.color_pair(C_WARN))
            win.refresh()
            shutil.rmtree(VENV_DIR)
            venv_exists = False
            content_y += 1

    if not venv_exists:
        safe_addstr(win, content_y, 6, "Creating virtual environment...",
                    curses.color_pair(C_WARN))
        win.refresh()
        draw_footer(win, "Running: python3 -m venv .venv")
        rc, out, err = run_cmd(["python3", "-m", "venv", str(VENV_DIR)],
                               cwd=REPO_ROOT)
        if rc != 0:
            safe_addstr(win, content_y, 6,
                        f"  [x] venv creation failed: {err[:60]}",
                        curses.color_pair(C_ERROR))
            content_y += 2
            wait_key(win, content_y, 6, "Press any key to exit...")
            return False
        safe_addstr(win, content_y, 6,
                    "  [+] Virtual environment created",
                    curses.color_pair(C_SUCCESS))
        content_y += 1

    # Install deps
    content_y += 1
    safe_addstr(win, content_y, 6, "Installing Python dependencies...",
                curses.color_pair(C_WARN))
    draw_footer(win, "Running: pip install -e . (this may take a moment)")
    win.refresh()

    pip = str(VENV_DIR / "bin" / "pip")
    rc, out, err = run_cmd([pip, "install", "-e", "."], cwd=REPO_ROOT,
                           timeout=300)
    content_y += 1
    if rc != 0:
        safe_addstr(win, content_y, 6,
                    f"  [x] pip install failed",
                    curses.color_pair(C_ERROR))
        content_y += 1
        # Show last few lines of error
        for line in err.split("\n")[-3:]:
            safe_addstr(win, content_y, 8, line[:max_x - 12],
                        curses.color_pair(C_ERROR))
            content_y += 1
        content_y += 1
        wait_key(win, content_y, 6, "Press any key to continue anyway...")
        return False

    safe_addstr(win, content_y, 6,
                "  [+] Dependencies installed successfully",
                curses.color_pair(C_SUCCESS))

    # Verify import
    content_y += 1
    python = str(VENV_DIR / "bin" / "python")
    rc, _, _ = run_cmd([python, "-c", "import bomba_sr; print('ok')"],
                       cwd=REPO_ROOT)
    if rc == 0:
        safe_addstr(win, content_y, 6,
                    "  [+] bomba_sr package imports OK",
                    curses.color_pair(C_SUCCESS))
    else:
        safe_addstr(win, content_y, 6,
                    "  [!] bomba_sr import check failed (may still work)",
                    curses.color_pair(C_WARN))

    content_y += 2
    wait_key(win, content_y, 6)
    return True


def step_frontend(win) -> bool:
    """Optionally install mission-control frontend deps."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 2)

    content_y = 5
    safe_addstr(win, content_y, 4, "Frontend Setup (Mission Control Dashboard)",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 2

    safe_addstr(win, content_y, 6,
                "The Mission Control dashboard provides a web UI for managing",
                curses.color_pair(C_DIM))
    content_y += 1
    safe_addstr(win, content_y, 6,
                "beings, tasks, orchestration, and memory. It's optional —",
                curses.color_pair(C_DIM))
    content_y += 1
    safe_addstr(win, content_y, 6,
                "the runtime works fine via CLI or HTTP API alone.",
                curses.color_pair(C_DIM))
    content_y += 2

    install_fe = confirm(win, content_y, 6,
                         "Install frontend dependencies?", default=True)
    content_y += 2

    if not install_fe:
        safe_addstr(win, content_y, 6,
                    "  Skipping frontend install.",
                    curses.color_pair(C_DIM))
        content_y += 2
        wait_key(win, content_y, 6)
        return False

    # Check if node_modules exists
    nm = MC_DIR / "node_modules"
    if nm.exists():
        safe_addstr(win, content_y, 6,
                    "node_modules/ already exists.",
                    curses.color_pair(C_SUCCESS))
        content_y += 1
        reuse = confirm(win, content_y, 6, "Skip npm install?", default=True)
        content_y += 1
        if reuse:
            safe_addstr(win, content_y, 6, "  [+] Using existing node_modules",
                        curses.color_pair(C_SUCCESS))
            content_y += 2
            wait_key(win, content_y, 6)
            return True

    safe_addstr(win, content_y, 6, "Installing frontend dependencies...",
                curses.color_pair(C_WARN))
    draw_footer(win, "Running: npm install in mission-control/")
    win.refresh()

    rc, out, err = run_cmd(["npm", "install"], cwd=MC_DIR, timeout=120)
    content_y += 1
    if rc != 0:
        safe_addstr(win, content_y, 6,
                    f"  [x] npm install failed",
                    curses.color_pair(C_ERROR))
        content_y += 1
        for line in err.split("\n")[-2:]:
            safe_addstr(win, content_y, 8, line[:max_x - 12],
                        curses.color_pair(C_ERROR))
            content_y += 1
        content_y += 1
        wait_key(win, content_y, 6, "Press any key to continue...")
        return False

    safe_addstr(win, content_y, 6,
                "  [+] Frontend dependencies installed",
                curses.color_pair(C_SUCCESS))
    content_y += 2
    wait_key(win, content_y, 6)
    return True


def step_api_keys(win) -> dict[str, str]:
    """Walk through API key configuration."""
    max_y, max_x = win.getmaxyx()

    # Load existing .env values if present
    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                v = v.strip()
                if v and not v.startswith("<"):
                    existing[k.strip()] = v

    # Group keys
    groups: dict[str, list[ApiKey]] = {}
    for k in API_KEYS:
        groups.setdefault(k.group, []).append(k)
        if k.env_var in existing:
            k.value = existing[k.env_var]

    group_labels = {
        "core": "Core LLM Providers",
        "web": "Web Search",
        "pinecone": "Pinecone Vector DB",
        "voice": "Voice (Bland.ai)",
        "zoom": "Zoom Integration",
    }

    for group_name, keys in groups.items():
        win.clear()
        draw_header(win, 3)

        content_y = 5
        label = group_labels.get(group_name, group_name.title())
        safe_addstr(win, content_y, 4, f"API Keys — {label}",
                    curses.color_pair(C_TITLE) | curses.A_BOLD)
        content_y += 2

        for key in keys:
            req_tag = " (REQUIRED)" if key.required else " (optional)"
            safe_addstr(win, content_y, 6,
                        f"{key.label}{req_tag}",
                        curses.color_pair(C_ACCENT) | curses.A_BOLD)
            content_y += 1
            safe_addstr(win, content_y, 8, key.description,
                        curses.color_pair(C_DIM))
            content_y += 1

            # Show existing value hint
            if key.value:
                masked = key.value[:4] + "..." + key.value[-4:] if len(key.value) > 12 else "***"
                safe_addstr(win, content_y, 8,
                            f"Current: {masked}",
                            curses.color_pair(C_SUCCESS))
                content_y += 1
                keep = confirm(win, content_y, 8, "Keep existing value?",
                               default=True)
                content_y += 1
                if keep:
                    content_y += 1
                    continue

            draw_footer(win, "Enter value (or press Enter to skip, ESC to skip)")
            val = text_input(win, content_y, 8, max_x - 16,
                             prompt=f"{key.env_var}=", secret=True)
            content_y += 1

            if val:
                key.value = val
                safe_addstr(win, content_y, 8,
                            "  [+] Set",
                            curses.color_pair(C_SUCCESS))
            elif key.required and not key.value:
                safe_addstr(win, content_y, 8,
                            "  [!] Required key not set — runtime will use echo provider",
                            curses.color_pair(C_WARN))
            else:
                safe_addstr(win, content_y, 8,
                            "  Skipped",
                            curses.color_pair(C_DIM))

            content_y += 2
            win.refresh()

            # Prevent overflowing screen
            if content_y >= max_y - 4:
                wait_key(win, content_y, 6)
                win.clear()
                draw_header(win, 3)
                content_y = 5
                safe_addstr(win, content_y, 4, f"API Keys — {label} (continued)",
                            curses.color_pair(C_TITLE) | curses.A_BOLD)
                content_y += 2

    result = {}
    for key in API_KEYS:
        if key.value:
            result[key.env_var] = key.value
    return result


def step_features(win, key_values: dict[str, str]) -> dict[str, bool]:
    """Feature module toggle screen."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 4)

    content_y = 5
    safe_addstr(win, content_y, 4, "Feature Modules",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 1
    safe_addstr(win, content_y, 4,
                "Toggle features on/off. Use arrow keys + Space to toggle, Enter to confirm.",
                curses.color_pair(C_DIM))
    content_y += 2

    # Pre-check: if required keys are set, default-enable the feature
    for feat in FEATURES:
        if feat.requires_keys:
            has_keys = all(k in key_values for k in feat.requires_keys)
            if has_keys:
                feat.enabled = True

    cursor = 0
    start_y = content_y

    def _draw():
        for i, feat in enumerate(FEATURES):
            y = start_y + i * 3
            if y >= max_y - 4:
                break
            is_sel = i == cursor
            box = "[x]" if feat.enabled else "[ ]"
            attr = curses.color_pair(C_HIGHLIGHT) if is_sel else curses.color_pair(C_NORMAL)
            label_attr = curses.A_BOLD if is_sel else 0

            safe_addstr(win, y, 6, f" {box} {feat.label} ",
                        attr | label_attr)
            safe_addstr(win, y + 1, 10, feat.description[:max_x - 14],
                        curses.color_pair(C_DIM))

            # Show missing key warning
            if feat.requires_keys:
                missing = [k for k in feat.requires_keys if k not in key_values]
                if missing and feat.enabled:
                    safe_addstr(win, y + 1, 10 + len(feat.description[:max_x - 14]) + 2,
                                "", 0)
                    warn_y = y + 2 if y + 2 < max_y - 4 else y + 1
                    safe_addstr(win, warn_y, 10,
                                f"  ! Missing: {', '.join(missing)}",
                                curses.color_pair(C_WARN))

        draw_footer(win, "Space=toggle  Enter=confirm  a=all on  n=all off")
        win.refresh()

    _draw()

    while True:
        ch = win.getch()
        if ch == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif ch == curses.KEY_DOWN:
            cursor = min(len(FEATURES) - 1, cursor + 1)
        elif ch == ord(" "):
            FEATURES[cursor].enabled = not FEATURES[cursor].enabled
        elif ch == ord("a"):
            for f in FEATURES:
                f.enabled = True
        elif ch == ord("n"):
            for f in FEATURES:
                f.enabled = False
        elif ch in (curses.KEY_ENTER, 10, 13):
            break

        # Redraw content area
        for y in range(start_y, max_y - 2):
            safe_addstr(win, y, 4, " " * (max_x - 8), 0)
        _draw()

    return {f.env_var: f.enabled for f in FEATURES}


def write_env_file(key_values: dict[str, str], features: dict[str, bool]):
    """Write the .env file from template + user values."""
    if not ENV_EXAMPLE.exists():
        # Fallback: write a minimal .env
        lines = []
        for k, v in key_values.items():
            lines.append(f"{k}={v}")
        for k, v in features.items():
            lines.append(f"{k}={'true' if v else 'false'}")
        ENV_FILE.write_text("\n".join(lines) + "\n")
        return

    template = ENV_EXAMPLE.read_text()
    result_lines = []
    written_vars: set[str] = set()

    for line in template.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            var_name = stripped.split("=", 1)[0].strip()
            if var_name in key_values:
                result_lines.append(f"{var_name}={key_values[var_name]}")
                written_vars.add(var_name)
                continue
            if var_name in features:
                result_lines.append(f"{var_name}={'true' if features[var_name] else 'false'}")
                written_vars.add(var_name)
                continue
        result_lines.append(line)

    # Append keys/features not found in the template
    extras = []
    for k, v in key_values.items():
        if k not in written_vars and v:
            extras.append(f"{k}={v}")
    for k, v in features.items():
        if k not in written_vars:
            extras.append(f"{k}={'true' if v else 'false'}")

    if extras:
        result_lines.append("")
        result_lines.append("# Additional configuration (added by installer)")
        result_lines.extend(extras)

    ENV_FILE.write_text("\n".join(result_lines) + "\n")


def step_bootstrap(win, key_values: dict[str, str],
                   features: dict[str, bool]) -> bool:
    """Write .env and run bootstrap."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 5)

    content_y = 5
    safe_addstr(win, content_y, 4, "Bootstrap & Configuration",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 2

    # Write .env
    safe_addstr(win, content_y, 6, "Writing .env configuration...",
                curses.color_pair(C_WARN))
    win.refresh()
    try:
        write_env_file(key_values, features)
        safe_addstr(win, content_y, 6,
                    "  [+] .env written successfully              ",
                    curses.color_pair(C_SUCCESS))
    except Exception as e:
        safe_addstr(win, content_y, 6,
                    f"  [x] Failed to write .env: {e}",
                    curses.color_pair(C_ERROR))
        content_y += 2
        wait_key(win, content_y, 6)
        return False
    content_y += 1

    # Run bootstrap
    safe_addstr(win, content_y, 6, "Running portable root bootstrap...",
                curses.color_pair(C_WARN))
    draw_footer(win, "Running: bootstrap_portable_root.py")
    win.refresh()

    python = str(VENV_DIR / "bin" / "python")
    bootstrap = str(REPO_ROOT / "scripts" / "bootstrap_portable_root.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    rc, out, err = run_cmd([python, bootstrap], cwd=REPO_ROOT)
    content_y += 1

    if rc != 0:
        safe_addstr(win, content_y, 6,
                    "  [!] Bootstrap returned non-zero (may be OK if dirs exist)",
                    curses.color_pair(C_WARN))
        content_y += 1
        if err:
            for line in err.split("\n")[:3]:
                safe_addstr(win, content_y, 8, line[:max_x - 12],
                            curses.color_pair(C_DIM))
                content_y += 1
    else:
        safe_addstr(win, content_y, 6,
                    "  [+] Portable root bootstrapped",
                    curses.color_pair(C_SUCCESS))

    # Run tests
    content_y += 2
    safe_addstr(win, content_y, 6,
                "Run quick test suite to verify install?",
                curses.color_pair(C_DIM))
    content_y += 1
    run_tests = confirm(win, content_y, 6, "Run tests?", default=False)
    content_y += 1

    if run_tests:
        safe_addstr(win, content_y, 6, "Running pytest...",
                    curses.color_pair(C_WARN))
        draw_footer(win, "Running: pytest -q (timeout 120s)")
        win.refresh()

        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        rc, out, err = run_cmd(
            [python, "-m", "pytest", "-q", "--tb=no"],
            cwd=REPO_ROOT, timeout=120,
        )
        content_y += 1
        if rc == 0:
            # Extract summary line
            last_line = out.strip().split("\n")[-1] if out else "passed"
            safe_addstr(win, content_y, 6,
                        f"  [+] Tests passed: {last_line[:60]}",
                        curses.color_pair(C_SUCCESS))
        else:
            last_line = out.strip().split("\n")[-1] if out else err[:60]
            safe_addstr(win, content_y, 6,
                        f"  [!] Tests: {last_line[:60]}",
                        curses.color_pair(C_WARN))

    content_y += 2

    # Summary
    safe_addstr(win, content_y, 4, "Configuration Summary",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 1

    n_keys = sum(1 for v in key_values.values() if v)
    n_features = sum(1 for v in features.values() if v)
    safe_addstr(win, content_y, 6,
                f"API keys configured: {n_keys}/{len(API_KEYS)}",
                curses.color_pair(C_DIM))
    content_y += 1
    safe_addstr(win, content_y, 6,
                f"Features enabled:    {n_features}/{len(FEATURES)}",
                curses.color_pair(C_DIM))
    content_y += 1

    enabled_names = [f.label for f in FEATURES if features.get(f.env_var)]
    if enabled_names:
        safe_addstr(win, content_y, 6,
                    f"Active: {', '.join(enabled_names)}"[:max_x - 10],
                    curses.color_pair(C_SUCCESS))
    content_y += 2

    wait_key(win, content_y, 6)
    return True


def step_launch(win, frontend_installed: bool) -> None:
    """Offer to launch services."""
    max_y, max_x = win.getmaxyx()
    win.clear()
    draw_header(win, 6)

    content_y = 5
    safe_addstr(win, content_y, 4, "Launch Services",
                curses.color_pair(C_TITLE) | curses.A_BOLD)
    content_y += 2

    safe_addstr(win, content_y, 6,
                "Installation complete! You can start the services now or later.",
                curses.color_pair(C_SUCCESS) | curses.A_BOLD)
    content_y += 2

    # Show manual commands
    safe_addstr(win, content_y, 4, "Manual start commands:",
                curses.color_pair(C_TITLE))
    content_y += 1

    cmds = [
        ("Backend",
         "source .venv/bin/activate && PYTHONPATH=src python scripts/run_runtime_server.py --host 127.0.0.1 --port 8787"),
        ("CLI",
         "source .venv/bin/activate && PYTHONPATH=src python scripts/run_chat_cli.py --tenant-id tenant-local --user-id user-local --workspace \"$(pwd)\""),
    ]
    if frontend_installed:
        cmds.append(("Frontend", "cd mission-control && npm run dev"))

    for label, cmd in cmds:
        safe_addstr(win, content_y, 6, f"{label}:",
                    curses.color_pair(C_ACCENT) | curses.A_BOLD)
        content_y += 1
        # Wrap long commands
        wrapped = textwrap.wrap(cmd, max_x - 12)
        for line in wrapped:
            safe_addstr(win, content_y, 8, line, curses.color_pair(C_DIM))
            content_y += 1
        content_y += 1

    safe_addstr(win, content_y, 4, "URLs (once running):",
                curses.color_pair(C_TITLE))
    content_y += 1
    safe_addstr(win, content_y, 6,
                f"Backend:   http://127.0.0.1:{BACKEND_PORT}",
                curses.color_pair(C_DIM))
    content_y += 1
    safe_addstr(win, content_y, 6,
                f"Health:    http://127.0.0.1:{BACKEND_PORT}/health",
                curses.color_pair(C_DIM))
    content_y += 1
    if frontend_installed:
        safe_addstr(win, content_y, 6,
                    f"Dashboard: http://127.0.0.1:{FRONTEND_PORT}",
                    curses.color_pair(C_DIM))
        content_y += 1

    content_y += 2

    launch = confirm(win, content_y, 6,
                     "Start the backend server now?", default=False)
    content_y += 2

    if launch:
        safe_addstr(win, content_y, 6,
                    "Starting backend in background...",
                    curses.color_pair(C_WARN))
        win.refresh()

        python = str(VENV_DIR / "bin" / "python")
        server = str(REPO_ROOT / "scripts" / "run_runtime_server.py")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")

        proc = subprocess.Popen(
            [python, server, "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=str(REPO_ROOT), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)

        if proc.poll() is None:
            safe_addstr(win, content_y, 6,
                        f"  [+] Backend started (PID {proc.pid})",
                        curses.color_pair(C_SUCCESS))
        else:
            safe_addstr(win, content_y, 6,
                        "  [x] Backend exited immediately — check .env config",
                        curses.color_pair(C_ERROR))
        content_y += 1

        if frontend_installed:
            content_y += 1
            launch_fe = confirm(win, content_y, 6,
                                "Also start the dashboard frontend?",
                                default=False)
            content_y += 1
            if launch_fe:
                subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=str(MC_DIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                safe_addstr(win, content_y, 6,
                            f"  [+] Frontend starting on port {FRONTEND_PORT}",
                            curses.color_pair(C_SUCCESS))
                content_y += 1

    content_y += 2
    safe_addstr(win, content_y, 4,
                "Setup complete!",
                curses.color_pair(C_SUCCESS) | curses.A_BOLD)
    content_y += 2
    wait_key(win, content_y, 6, "Press any key to exit installer...")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def main(stdscr):
    curses.curs_set(0)
    init_colors()
    stdscr.timeout(-1)

    # Step 1: Prerequisites
    results = step_prerequisites(stdscr)
    if not results:
        return

    # Step 2: Python environment
    if not step_python_env(stdscr):
        # Allow continuing even on failure
        pass

    # Step 3: Frontend
    frontend_installed = step_frontend(stdscr)

    # Step 4: API keys
    key_values = step_api_keys(stdscr)

    # Step 5: Feature modules
    features = step_features(stdscr, key_values)

    # Step 6: Bootstrap
    step_bootstrap(stdscr, key_values, features)

    # Step 7: Launch
    step_launch(stdscr, frontend_installed)


if __name__ == "__main__":
    # Minimum terminal size check
    try:
        size = os.get_terminal_size()
        if size.columns < 80 or size.lines < 24:
            print(f"Terminal too small ({size.columns}x{size.lines}). "
                  f"Need at least 80x24.")
            sys.exit(1)
    except OSError:
        pass

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nInstaller cancelled.")
        sys.exit(0)
