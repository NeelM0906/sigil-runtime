from __future__ import annotations

from enum import Enum


class ToolProfile(Enum):
    MINIMAL = "minimal"
    CODING = "coding"
    RESEARCH = "research"
    FULL = "full"


TOOL_GROUPS: dict[str, set[str]] = {
    "group:runtime": {"exec", "process", "compact_context", "switch_model", "enable_tools"},
    "group:fs": {"read", "write", "edit", "apply_patch", "glob", "grep"},
    "group:codeintel": {
        "code_search",
        "get_symbols_overview",
        "find_symbol",
        "find_referencing_symbols",
        "replace_symbol_body",
        "insert_before_symbol",
        "insert_after_symbol",
        "rename_symbol",
    },
    "group:memory": {"memory_search", "memory_get", "memory_store"},
    "group:web": {"web_search", "web_fetch"},
    "group:sessions": {"sessions_list", "sessions_send", "sessions_spawn", "sessions_poll", "session_status"},
    "group:approvals": {"list_approvals", "decide_approval"},
    "group:skills": {"skill_create", "skill_update", "skill_install_request", "skill_install_apply"},
}


TOOL_ALIASES: dict[str, str] = {
    "read_file": "read",
    "write_file": "write",
    "edit_file": "edit",
    "exec_command": "exec",
    "glob_files": "glob",
    "grep_content": "grep",
    "spawn_subagent": "sessions_spawn",
    "poll_subagent": "sessions_poll",
}


def resolve_alias(name: str) -> str:
    return TOOL_ALIASES.get(name, name)


def _expand(*items: str) -> set[str]:
    out: set[str] = set()
    for item in items:
        if item.startswith("group:"):
            out.update(TOOL_GROUPS.get(item, set()))
            continue
        out.add(item)
    return out


PROFILE_TOOLS: dict[ToolProfile, set[str] | None] = {
    ToolProfile.MINIMAL: {"session_status"},
    ToolProfile.CODING: _expand(
        "group:fs",
        "group:runtime",
        "group:codeintel",
        "group:memory",
        "group:sessions",
        "group:approvals",
        "group:skills",
    ),
    ToolProfile.RESEARCH: _expand("group:web", "group:memory", "group:fs") - {"write", "edit", "apply_patch"},
    ToolProfile.FULL: None,
}


def profile_from_value(value: str | ToolProfile) -> ToolProfile:
    if isinstance(value, ToolProfile):
        return value
    normalized = str(value).strip().lower()
    for profile in ToolProfile:
        if profile.value == normalized:
            return profile
    return ToolProfile.FULL
