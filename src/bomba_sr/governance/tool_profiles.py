from __future__ import annotations


TOOL_GROUPS: dict[str, set[str]] = {
    "group:runtime": {
        "exec",
        "process",
        "compact_context",
        "switch_model",
        "enable_tools",
    },
    "group:exec": {"exec", "process"},
    "group:cron": {
        "schedule_task",
        "list_schedules",
        "remove_schedule",
        "set_schedule_enabled",
    },
    "group:fs": {"read", "write", "edit", "apply_patch", "glob", "grep", "parse_document", "create_deliverable", "list_deliverables"},
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
    "group:memory": {"memory_search", "memory_store"},
    "group:web": {"web_search", "web_fetch"},
    "group:sessions": {"sessions_list", "sessions_send", "sessions_spawn", "sessions_poll", "session_status"},
    "group:approvals": {"list_approvals", "decide_approval"},
    "group:skills": {"skill_create", "skill_update", "skill_list"},
    "group:seo": {
        "seo_people_also_ask", "seo_autocomplete", "seo_reddit_quora",
        "seo_keyword_clusters", "seo_content_explorer", "seo_semantic_keywords",
        "seo_ai_assistant", "seo_full_research",
    },
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
