from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bomba_sr.openclaw.integration import discover_colosseum_data_roots


def _split_env(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    raw = value.replace(";", ":").replace(",", ":")
    out: list[str] = []
    for part in raw.split(":"):
        item = part.strip()
        if item:
            out.append(item)
    return tuple(out)


def _json_dict_env(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return dict(payload)


def _portable_openclaw_model_default() -> str:
    config_path = Path(__file__).resolve().parents[3] / "portable-openclaw" / "openclaw.json"
    if config_path.is_file():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        agents = payload.get("agents") if isinstance(payload, dict) else {}
        if isinstance(agents, dict):
            for item in agents.get("list") or []:
                if isinstance(item, dict) and str(item.get("id") or "").strip() == "main":
                    model = item.get("model")
                    if isinstance(model, dict) and str(model.get("primary") or "").strip():
                        return str(model.get("primary") or "").strip().removeprefix("openrouter/")
                    if isinstance(model, str) and model.strip():
                        return model.strip().removeprefix("openrouter/")
            defaults = agents.get("defaults")
            if isinstance(defaults, dict) and str(defaults.get("model") or "").strip():
                return str(defaults.get("model") or "").strip().removeprefix("openrouter/")
    return "anthropic/claude-opus-4.6"


@dataclass(frozen=True)
class SerenaPolicy:
    enabled: bool = True
    edit_tools_enabled: bool = True
    shell_tool_enabled: bool = False
    base_url: str = os.getenv("SERENA_BASE_URL", "http://127.0.0.1:9121")
    api_key: str | None = os.getenv("SERENA_API_KEY")
    fallback_to_native: bool = os.getenv("SERENA_FALLBACK_TO_NATIVE", "true").lower() != "false"
    allowed_tools: tuple[str, ...] = (
        "get_symbols_overview",
        "find_symbol",
        "find_referencing_symbols",
        "replace_symbol_body",
        "insert_before_symbol",
        "insert_after_symbol",
        "rename_symbol",
    )


@dataclass(frozen=True)
class RuntimeConfig:
    runtime_home: Path = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime")).resolve()
    default_model_id: str = os.getenv("BOMBA_MODEL_ID", _portable_openclaw_model_default())
    serena: SerenaPolicy = field(default_factory=SerenaPolicy)
    learning_auto_apply_confidence: float = float(os.getenv("BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE", "0.4"))
    capability_cache_ttl_seconds: int = int(os.getenv("BOMBA_CAPABILITY_CACHE_TTL_SECONDS", str(6 * 60 * 60)))
    generic_info_web_retrieval_enabled: bool = os.getenv("BOMBA_GENERIC_INFO_WEB_RETRIEVAL", "true").lower() != "false"
    skill_roots: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_SKILL_ROOTS")))
    skill_watcher_enabled: bool = os.getenv("BOMBA_SKILL_WATCHER", "true").lower() != "false"
    skill_watcher_debounce_ms: int = int(os.getenv("BOMBA_SKILL_WATCHER_DEBOUNCE_MS", "250"))
    plugin_paths: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_PLUGIN_PATHS")))
    plugin_allow: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_PLUGIN_ALLOW")))
    plugin_deny: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_PLUGIN_DENY")))
    tool_allow: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_TOOL_ALLOW")))
    tool_deny: tuple[str, ...] = field(default_factory=lambda: _split_env(os.getenv("BOMBA_TOOL_DENY")))
    max_loop_iterations: int = int(os.getenv("BOMBA_MAX_LOOP_ITERATIONS", "75"))
    loop_detection_window: int = int(os.getenv("BOMBA_LOOP_DETECTION_WINDOW", "5"))
    agentic_loop_enabled: bool = os.getenv("BOMBA_AGENTIC_LOOP_ENABLED", "true").lower() != "false"
    budget_limit_usd: float = float(os.getenv("BOMBA_BUDGET_LIMIT_USD", "50.0"))
    budget_hard_stop_pct: float = float(os.getenv("BOMBA_BUDGET_HARD_STOP_PCT", "0.95"))
    tool_result_max_chars: int = int(os.getenv("BOMBA_TOOL_RESULT_MAX_CHARS", "15000"))
    shell_output_max_chars: int = int(os.getenv("BOMBA_SHELL_OUTPUT_MAX_CHARS", "50000"))
    parallel_read_tools: bool = os.getenv("BOMBA_PARALLEL_READ_TOOLS", "true").lower() != "false"
    rescue_enabled: bool = os.getenv("BOMBA_RESCUE_ENABLED", "true").lower() != "false"
    subagent_crash_window_seconds: float = float(os.getenv("BOMBA_SUBAGENT_CRASH_WINDOW", "60"))
    subagent_crash_max: int = int(os.getenv("BOMBA_SUBAGENT_CRASH_MAX", "3"))
    subagent_crash_cooldown_seconds: float = float(os.getenv("BOMBA_SUBAGENT_CRASH_COOLDOWN", "120"))
    subagent_max_spawn_depth: int = int(os.getenv("BOMBA_SUBAGENT_MAX_SPAWN_DEPTH", "3"))
    adaptation_metrics_interval: int = int(os.getenv("BOMBA_ADAPTATION_METRICS_INTERVAL", "5"))
    adaptation_llm_eval_interval: int = int(os.getenv("BOMBA_ADAPTATION_LLM_EVAL_INTERVAL", "10"))
    adaptation_auto_correct: bool = os.getenv("BOMBA_ADAPTATION_AUTO_CORRECT", "true").lower() != "false"
    heartbeat_enabled: bool = os.getenv("BOMBA_HEARTBEAT_ENABLED", "false").lower() != "false"
    heartbeat_interval_seconds: int = int(os.getenv("BOMBA_HEARTBEAT_INTERVAL", "1800"))
    cron_enabled: bool = os.getenv("BOMBA_CRON_ENABLED", "true").lower() != "false"
    dream_cycle_enabled: bool = os.getenv("BOMBA_DREAM_CYCLE_ENABLED", "false").lower() != "false"
    dream_cycle_interval_seconds: int = int(os.getenv("BOMBA_DREAM_CYCLE_INTERVAL", "3600"))
    replay_history_budget_fraction: float = float(os.getenv("BOMBA_REPLAY_HISTORY_BUDGET_FRACTION", "0.7"))
    web_search_enabled: bool = os.getenv("BOMBA_WEB_SEARCH_ENABLED", "true").lower() != "false"
    brave_api_key: str | None = os.getenv("BRAVE_API_KEY")
    pinecone_enabled: bool = os.getenv(
        "BOMBA_PINECONE_ENABLED",
        "true" if os.getenv("PINECONE_API_KEY") else "false",
    ).lower() != "false"
    pinecone_default_index: str = os.getenv("BOMBA_PINECONE_DEFAULT_INDEX", "ublib2")
    pinecone_default_namespace: str = os.getenv("BOMBA_PINECONE_DEFAULT_NAMESPACE", "longterm")
    supabase_enabled: bool = os.getenv(
        "BOMBA_SUPABASE_ENABLED",
        "true" if os.getenv("SUPABASE_URL") and (
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        ) else "false",
    ).lower() != "false"
    postgres_enabled: bool = os.getenv(
        "BOMBA_POSTGRES_ENABLED",
        "true" if os.getenv("DATABASE_URL") else "false",
    ).lower() != "false"
    voice_enabled: bool = os.getenv(
        "BOMBA_VOICE_ENABLED",
        "true" if os.getenv("BLAND_API_KEY") else "false",
    ).lower() != "false"
    voice_provider: str = os.getenv("BOMBA_VOICE_PROVIDER", "bland")
    fal_enabled: bool = os.getenv(
        "BOMBA_FAL_ENABLED",
        "true" if (os.getenv("FAL_KEY") or os.getenv("FAL_KEY_NEW")) else "false",
    ).lower() != "false"
    fal_video_model: str = os.getenv("BOMBA_FAL_VIDEO_MODEL", "fal-ai/wan/v2.2-a14b/text-to-video")
    colosseum_enabled: bool = os.getenv(
        "BOMBA_COLOSSEUM_ENABLED",
        "true" if discover_colosseum_data_roots() else "false",
    ).lower() != "false"
    colosseum_model_id: str = os.getenv("BOMBA_COLOSSEUM_MODEL_ID", _portable_openclaw_model_default())
    prove_ahead_enabled: bool = os.getenv("BOMBA_PROVE_AHEAD_ENABLED", "false").lower() != "false"
    team_manager_enabled: bool = os.getenv("BOMBA_TEAM_MANAGER_ENABLED", "false").lower() != "false"
    team_manager_model_id: str = os.getenv("BOMBA_TEAM_MANAGER_MODEL_ID", "")
    skill_parsing_permissive: bool = os.getenv("BOMBA_SKILL_PARSING_PERMISSIVE", "true").lower() != "false"
    skills_telemetry_enabled: bool = os.getenv("BOMBA_SKILLS_TELEMETRY_ENABLED", "true").lower() != "false"
    skill_nl_router_enabled: bool = os.getenv("BOMBA_SKILL_NL_ROUTER_ENABLED", "true").lower() != "false"
    skill_catalog_sources: tuple[str, ...] = field(
        default_factory=lambda: _split_env(os.getenv("BOMBA_SKILL_CATALOG_SOURCES", "clawhub,anthropic_skills"))
    )
    skill_source_repo_overrides: dict[str, Any] = field(
        default_factory=lambda: _json_dict_env(os.getenv("BOMBA_SKILL_SOURCE_REPO_OVERRIDES"))
    )
    clawhub_api_base: str | None = os.getenv("CLAWHUB_API_BASE")

    def __post_init__(self) -> None:
        if not (0.0 <= self.learning_auto_apply_confidence <= 1.0):
            raise ValueError("learning_auto_apply_confidence must be in [0,1]")
        if self.capability_cache_ttl_seconds <= 0:
            raise ValueError("capability_cache_ttl_seconds must be > 0")
        if self.skill_watcher_debounce_ms < 50:
            raise ValueError("skill_watcher_debounce_ms must be >= 50")
        if self.max_loop_iterations < 1:
            raise ValueError("max_loop_iterations must be >= 1")
        if self.loop_detection_window < 1:
            raise ValueError("loop_detection_window must be >= 1")
        if self.budget_limit_usd <= 0:
            raise ValueError("budget_limit_usd must be > 0")
        if not (0.0 < self.budget_hard_stop_pct <= 1.0):
            raise ValueError("budget_hard_stop_pct must be in (0,1]")
        if self.tool_result_max_chars <= 0:
            raise ValueError("tool_result_max_chars must be > 0")
        if self.shell_output_max_chars <= 0:
            raise ValueError("shell_output_max_chars must be > 0")
        if self.subagent_crash_window_seconds <= 0:
            raise ValueError("subagent_crash_window_seconds must be > 0")
        if self.subagent_crash_max < 1:
            raise ValueError("subagent_crash_max must be >= 1")
        if self.subagent_crash_cooldown_seconds < 0:
            raise ValueError("subagent_crash_cooldown_seconds must be >= 0")
        if self.subagent_max_spawn_depth < 1:
            raise ValueError("subagent_max_spawn_depth must be >= 1")
        if self.adaptation_metrics_interval < 1:
            raise ValueError("adaptation_metrics_interval must be >= 1")
        if self.adaptation_llm_eval_interval < 1:
            raise ValueError("adaptation_llm_eval_interval must be >= 1")
        if self.heartbeat_interval_seconds < 1:
            raise ValueError("heartbeat_interval_seconds must be >= 1")
        if not (0.0 < self.replay_history_budget_fraction <= 1.0):
            raise ValueError("replay_history_budget_fraction must be in (0,1]")
        if not self.skill_catalog_sources:
            raise ValueError("skill_catalog_sources must not be empty")
        if not self.pinecone_default_index.strip():
            raise ValueError("pinecone_default_index must not be empty")
        if not self.voice_provider.strip():
            raise ValueError("voice_provider must not be empty")
