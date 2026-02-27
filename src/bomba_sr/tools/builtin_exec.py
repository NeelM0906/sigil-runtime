from __future__ import annotations

import shlex
import subprocess
import threading
from pathlib import Path
from typing import Any

from bomba_sr.tools.base import ToolContext, ToolDefinition


_PROC_LOCK = threading.Lock()
_PROC_REGISTRY: dict[int, subprocess.Popen[str]] = {}


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars < 1 or len(text) <= max_chars:
        return text
    half = max_chars // 2
    omitted = len(text) - max_chars
    return text[:half] + f"\n\n... [{omitted} chars truncated] ...\n\n" + text[-half:]


def _exec_tool(arguments: dict[str, Any], context: ToolContext, default_max_output_chars: int = 50000) -> dict[str, Any]:
    command = str(arguments.get("command") or "").strip()
    if not command:
        raise ValueError("command is required")
    timeout = int(arguments.get("timeout") or 120)
    cwd_raw = str(arguments.get("cwd") or ".")
    cwd = context.guard_path(cwd_raw)
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    max_chars = int(arguments.get("max_output_chars") or default_max_output_chars)
    stdout = _truncate_text(proc.stdout, max_chars)
    stderr = _truncate_text(proc.stderr, max_chars)
    return {
        "command": command,
        "cwd": str(cwd),
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": proc.returncode,
    }


def _process_tool(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    action = str(arguments.get("action") or "list")
    if action == "list":
        with _PROC_LOCK:
            items = [
                {"pid": pid, "running": (proc.poll() is None), "args": shlex.join(proc.args if isinstance(proc.args, list) else [str(proc.args)])}
                for pid, proc in _PROC_REGISTRY.items()
            ]
        return {"processes": items}

    if action == "kill":
        pid = int(arguments.get("pid") or 0)
        if pid <= 0:
            raise ValueError("pid is required for kill")
        with _PROC_LOCK:
            proc = _PROC_REGISTRY.get(pid)
        if proc is None:
            return {"killed": False, "reason": "pid_not_found", "pid": pid}
        proc.kill()
        with _PROC_LOCK:
            _PROC_REGISTRY.pop(pid, None)
        return {"killed": True, "pid": pid}

    raise ValueError(f"unsupported process action: {action}")


def builtin_exec_tools(default_max_output_chars: int = 50000) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="exec",
            description="Execute a shell command in the workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "cwd": {"type": "string"},
                    "max_output_chars": {"type": "integer"},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            risk_level="critical",
            action_type="execute_shell_command",
            execute=lambda arguments, context: _exec_tool(
                arguments=arguments,
                context=context,
                default_max_output_chars=default_max_output_chars,
            ),
            aliases=("exec_command",),
        ),
        ToolDefinition(
            name="process",
            description="List or kill background processes managed by the runtime.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "kill"]},
                    "pid": {"type": "integer"},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_process_tool,
        ),
    ]
