"""
Per-being tool profiles.

ACT-I Standard: "Only include tools the being actually needs.
Every unnecessary tool reference eats tokens."

Each profile defines the tool names a being has access to.
Tools not in the being's profile are denied before serialization,
saving ~200 tokens per excluded tool per turn.
"""
from __future__ import annotations

from bomba_sr.governance.tool_profiles import TOOL_GROUPS


# ── Extended tool groups (supplement tool_profiles.py) ─────────────────
# These cover tool categories not in the original TOOL_GROUPS.

TOOL_GROUPS_EXT: dict[str, set[str]] = {
    "group:pinecone": {
        "pinecone_query",
        "pinecone_list_indexes",
        "pinecone_upsert",
        "pinecone_multi_query",
    },
    "group:voice": {
        "voice_list_calls",
        "voice_get_transcript",
        "voice_make_call",
        "voice_list_pathways",
    },
    "group:colosseum": {
        "colosseum_run_round",
        "colosseum_leaderboard",
        "colosseum_being_list",
        "colosseum_evolve",
        "colosseum_scenario_list",
    },
    "group:prove_ahead": {
        "prove_ahead_competitors",
        "prove_ahead_matrix",
        "prove_ahead_benchmark",
        "prove_ahead_report",
    },
    "group:projects": {
        "project_create",
        "project_list",
        "task_create",
        "task_list",
        "task_update",
    },
    "group:scheduler": {
        "schedule_task",
        "list_schedules",
        "remove_schedule",
        "set_schedule_enabled",
    },
    "group:sisters": {
        "sisters_list",
        "sisters_spawn",
        "sisters_stop",
        "sisters_status",
        "sisters_message",
    },
    "group:team": {
        "team_graph_create",
        "team_graph_list",
        "team_node_add",
        "team_node_list",
        "team_edge_add",
        "team_graph_validate",
        "team_variable_set",
        "team_pipeline_save",
        "team_deploy",
        "team_deploy_start",
        "team_deploy_status",
        "team_deploy_list",
        "team_deploy_cancel",
        "team_deploy_primer",
        "team_schedule_create",
        "team_schedule_list",
        "team_schedule_update",
        "team_schedule_delete",
        "team_schedule_toggle",
    },
    "group:model_discovery": {
        "switch_model",
        "enable_tools",
        "compact_context",
    },
    "group:knowledge": {"update_knowledge"},
    "group:team_context": {"update_team_context"},
}


def _expand_groups(*items: str) -> set[str]:
    """Expand group references into flat tool name sets."""
    out: set[str] = set()
    for item in items:
        if item.startswith("group:"):
            found = TOOL_GROUPS.get(item) or TOOL_GROUPS_EXT.get(item)
            if found:
                out.update(found)
            continue
        out.add(item)
    return out


# ── Per-tenant tool allow-lists ────────────────────────────────────────
# None = full access (no filtering). frozenset = only these tools allowed.
# Tenant IDs map to tool sets. If a tenant isn't listed, it gets full access.

TENANT_TOOL_PROFILES: dict[str, frozenset[str] | None] = {
    # Prime (tenant-local / tenant-prime) — full access
    "tenant-local": None,
    "tenant-prime": None,

    # Forge — creative + code + production
    "tenant-forge": frozenset(_expand_groups(
        "group:fs",            # read, write, edit, apply_patch, glob, grep
        "group:memory",        # memory_search, memory_get, memory_store
        "group:web",           # web_search, web_fetch
        "group:pinecone",      # pinecone_query, pinecone_multi_query, pinecone_upsert, pinecone_list_indexes
        "group:runtime",       # exec, process, compact_context, switch_model, etc.
        "group:codeintel",     # code_search + serena symbol tools
        "group:skills",        # skill_create, skill_update, skill_install_*
        "group:knowledge",     # update_knowledge
        "group:sessions",      # sessions_spawn, sessions_poll, sessions_list
        "group:colosseum",     # colosseum tools — Forge's core domain
    )),

    # Scholar — research + retrieval
    "tenant-scholar": frozenset(_expand_groups(
        "group:memory",        # memory_search, memory_get, memory_store
        "group:web",           # web_search, web_fetch
        "group:pinecone",      # pinecone_query, pinecone_multi_query, pinecone_upsert, pinecone_list_indexes
        "group:fs",            # read, write, edit, glob, grep (for reports)
        "group:knowledge",     # update_knowledge
    )),

    # Recovery — CRM + outreach + voice + memory
    "tenant-recovery": frozenset(_expand_groups(
        "group:memory",        # memory_search, memory_get, memory_store
        "group:web",           # web_search, web_fetch
        "group:pinecone",      # pinecone_query, pinecone_multi_query, pinecone_upsert, pinecone_list_indexes
        "group:voice",         # voice_list_calls, voice_get_transcript, voice_make_call, voice_list_pathways
        "group:fs",            # read, write, edit, glob, grep (for case files)
        "group:knowledge",     # update_knowledge
        "group:sessions",      # sessions_spawn, sessions_poll (for BD-PIP, BD-WC sub-agents)
    )),

    # Memory — memory specialist + Pinecone
    "tenant-memory": frozenset(_expand_groups(
        "group:memory",        # memory_search, memory_get, memory_store — core domain
        "group:pinecone",      # ALL pinecone tools — Memory's signature move
        "group:fs",            # read, write, edit, glob, grep (for memory files)
        "group:web",           # web_search (for grounding in current facts)
        "group:knowledge",     # update_knowledge
    )),
}


def get_denied_tools_for_tenant(tenant_id: str, all_tools: list[str]) -> frozenset[str]:
    """Return the set of tool names that should be denied for a given tenant.

    If the tenant has no profile (or profile is None/full), returns empty set.
    Otherwise, returns all registered tools NOT in the tenant's allow-list.
    """
    allowed = TENANT_TOOL_PROFILES.get(tenant_id)
    if allowed is None:
        return frozenset()
    return frozenset(t for t in all_tools if t not in allowed)
