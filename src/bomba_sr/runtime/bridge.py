from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bomba_sr.adaptation.runtime_adaptation import RuntimeAdaptationEngine
from bomba_sr.adaptation.self_evaluation import SelfEvaluator
from bomba_sr.autonomy.heartbeat import HeartbeatEngine
from bomba_sr.autonomy.scheduler import CronScheduler
from bomba_sr.memory.dreaming import DreamCycle
from bomba_sr.artifacts.store import ArtifactStore
from bomba_sr.codeintel.router import CodeIntelRouter
from bomba_sr.commands.disclosure import SkillDisclosure
from bomba_sr.commands.parser import CommandParser
from bomba_sr.commands.router import CommandContext, CommandRouter
from bomba_sr.commands.skill_nl_router import parse_skill_nl_intent
from bomba_sr.context.policy import ContextPolicyEngine, TurnProfile, calculate_budget, estimate_tokens
from bomba_sr.governance.being_tool_profiles import get_denied_tools
from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.identity.profile import UserIdentityService
from bomba_sr.identity.soul import SoulConfig, load_soul_from_workspace
from bomba_sr.info.retrieval import GenericInfoRetriever
from bomba_sr.llm.providers import ChatMessage, LLMProvider, provider_from_env
from bomba_sr.memory.embeddings import OpenAIEmbeddingProvider, default_embedding_api_key
from bomba_sr.memory.hybrid import HybridMemoryStore, resolve_being_id
from bomba_sr.models.capabilities import CapabilityError, ModelCapabilityService
from bomba_sr.openclaw.integration import ensure_portable_openclaw_layout, list_skill_roots
from bomba_sr.plugins.registry import PluginRegistry
from bomba_sr.projects.service import ProjectService
from bomba_sr.runtime.config import RuntimeConfig
from bomba_sr.runtime.loop import AgenticLoop, LoopConfig
from bomba_sr.runtime.rescue import WorkspaceRescue
from bomba_sr.runtime.sisters import SisterRegistry
from bomba_sr.runtime.tenancy import TenantContext, TenantRegistry
from bomba_sr.search.agentic_search import AgenticSearchExecutor, SearchPlan, result_pack_to_dict
from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.engine import SkillEngine
from bomba_sr.skills.ecosystem import SkillEcosystemService
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.orchestrator import CrashStormConfig, SubAgentHandle, SubAgentOrchestrator, SubAgentWorker
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask
from bomba_sr.tools.base import ToolContext, ToolExecutor
from bomba_sr.tools.builtin_approvals import builtin_approval_tools
from bomba_sr.tools.builtin_colosseum import builtin_colosseum_tools
from bomba_sr.tools.builtin_compaction import builtin_compaction_tools
from bomba_sr.tools.builtin_discovery import builtin_discovery_tools
from bomba_sr.tools.builtin_exec import builtin_exec_tools
from bomba_sr.tools.builtin_fal import builtin_fal_tools
from bomba_sr.tools.builtin_fs import builtin_fs_tools
from bomba_sr.tools.builtin_knowledge import builtin_knowledge_tools
from bomba_sr.tools.builtin_team_context import builtin_team_context_tools
from bomba_sr.tools.builtin_memory import builtin_memory_tools
from bomba_sr.tools.builtin_model_switch import builtin_model_switch_tools
from bomba_sr.tools.builtin_pinecone import builtin_pinecone_tools
from bomba_sr.tools.builtin_projects import builtin_project_tools
from bomba_sr.tools.builtin_prove_ahead import builtin_prove_ahead_tools
from bomba_sr.tools.builtin_search import builtin_search_tools
from bomba_sr.tools.builtin_scheduler import builtin_scheduler_tools
from bomba_sr.tools.builtin_skills import builtin_skill_tools
from bomba_sr.tools.builtin_sisters import builtin_sister_tools
from bomba_sr.tools.builtin_subagents import builtin_subagent_tools
from bomba_sr.tools.builtin_data_access import builtin_data_access_tools
from bomba_sr.tools.builtin_voice import builtin_voice_tools
from bomba_sr.tools.builtin_web import builtin_web_tools
from bomba_sr.tools.builtin_browser import builtin_browser_tools

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TurnRequest:
    tenant_id: str
    session_id: str
    user_id: str
    user_message: str
    turn_id: str | None = None
    model_id: str | None = None
    profile: TurnProfile = TurnProfile.CHAT
    workspace_root: str | None = None
    search_query: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    max_loop_iterations: int | None = None
    on_iteration: Any = None
    disable_tools: bool = False
    include_representation: bool = False


@dataclass
class _TenantRuntime:
    context: TenantContext
    db: RuntimeDB
    capabilities: ModelCapabilityService
    context_engine: ContextPolicyEngine
    search: AgenticSearchExecutor
    memory: HybridMemoryStore
    protocol: SubAgentProtocol
    orchestrator: SubAgentOrchestrator
    adaptation: RuntimeAdaptationEngine
    artifacts: ArtifactStore
    codeintel: CodeIntelRouter
    governance: ToolGovernanceService
    projects: ProjectService
    skills_registry: SkillRegistry
    skills_engine: SkillEngine
    skill_loader: SkillLoader
    skills_ecosystem: SkillEcosystemService
    plugin_registry: PluginRegistry
    policy_pipeline: PolicyPipeline
    tool_executor: ToolExecutor
    command_parser: CommandParser
    command_router: CommandRouter
    skill_disclosure: SkillDisclosure
    identity: UserIdentityService
    soul: SoulConfig | None
    sisters: SisterRegistry | None
    info: GenericInfoRetriever
    team_manager: Any | None


def _strip_tool_blocks(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove tool_use and tool_result content blocks, keep text only.

    Ensures orchestration/subtask replay messages don't contain stale
    tool blocks that can cause API errors when replayed.
    """
    cleaned: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "")
        if role == "tool":
            continue  # Skip tool result messages entirely
        content = msg.get("content")
        if isinstance(content, list):
            # Filter to text-only blocks
            text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]
            if text_blocks:
                cleaned.append({**msg, "content": text_blocks})
        elif isinstance(content, str):
            cleaned.append(msg)
    return cleaned


class RuntimeBridge:
    def __init__(
        self,
        config: RuntimeConfig | None = None,
        provider: LLMProvider | None = None,
        serena_transport: Any | None = None,
        embedding_provider: OpenAIEmbeddingProvider | None = None,
    ) -> None:
        self.config = config or RuntimeConfig()
        ensure_portable_openclaw_layout()
        self.provider = provider or provider_from_env()
        self.registry = TenantRegistry(self.config.runtime_home)
        self.serena_transport = serena_transport
        self.embedding_provider = embedding_provider
        default_embed_key = default_embedding_api_key()
        if self.embedding_provider is None and default_embed_key:
            self.embedding_provider = OpenAIEmbeddingProvider(api_key=default_embed_key)
        self._tenants: dict[str, _TenantRuntime] = {}
        self._tenants_lock = threading.Lock()
        self._heartbeat_engines: dict[str, HeartbeatEngine] = {}
        self._cron_schedulers: dict[str, CronScheduler] = {}
        self._dream_cycle: DreamCycle | None = None
        self._start_time: float = time.time()

    def handle_turn(self, request: TurnRequest) -> dict[str, Any]:
        runtime = self._tenant_runtime(request.tenant_id, request.workspace_root)
        turn_id = request.turn_id or str(uuid.uuid4())
        model_id = request.model_id or self.config.default_model_id
        _being_id_for_write = resolve_being_id(request.session_id, request.user_id)

        effective_user_message = request.user_message
        selected_skill_context = ""

        if runtime.command_parser.is_command(request.user_message):
            parsed = runtime.command_parser.parse(request.user_message)
            if parsed is not None:
                command_policy = runtime.policy_pipeline.resolve(
                    ToolPolicyContext(
                        profile=self.config.tool_profile,
                        tenant_id=request.tenant_id,
                        provider_name=self.provider.provider_name,
                    ),
                    available_tools=runtime.tool_executor.known_tool_names(),
                )
                command_ctx = CommandContext(
                    tool_context=ToolContext(
                        tenant_id=request.tenant_id,
                        session_id=request.session_id,
                        turn_id=turn_id,
                        user_id=request.user_id,
                        workspace_root=runtime.context.workspace_root,
                        db=runtime.db,
                        guard_path=lambda p: self.registry.guard_path(runtime.context, p),
                    ),
                    policy=command_policy,
                    profile_lookup=lambda: runtime.identity.get_profile(request.tenant_id, request.user_id),
                )
                cmd_result = runtime.command_router.route(parsed, command_ctx)
                if cmd_result.handled and cmd_result.bypass_llm:
                    payload_text = json.dumps(cmd_result.output or {}, indent=2, ensure_ascii=True)
                    self._record_conversation_turn(
                        runtime=runtime,
                        request=request,
                        turn_id=turn_id,
                        user_message=request.user_message,
                        assistant_message=payload_text,
                    )
                    return {
                        "tenant": {
                            "tenant_id": request.tenant_id,
                            "workspace_root": str(runtime.context.workspace_root),
                            "db_path": str(runtime.context.db_path),
                        },
                        "turn": {
                            "session_id": request.session_id,
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "capability_source": "n/a",
                            "profile": request.profile.value,
                            "mode": "command",
                            "project_id": request.project_id,
                            "task_id": request.task_id,
                        },
                        "assistant": {
                            "text": payload_text,
                            "provider": "command_router",
                            "usage": None,
                        },
                        "memory": {"pending_approvals": runtime.memory.pending_approvals(request.tenant_id, request.user_id)},
                        "identity": {
                            "profile": runtime.identity.get_profile(request.tenant_id, request.user_id),
                            "newly_applied_signals": [],
                            "pending_signals": runtime.identity.list_pending_signals(request.tenant_id, request.user_id),
                        },
                        "artifacts": [],
                    }
                if cmd_result.handled and cmd_result.skill_body:
                    selected_skill_context = cmd_result.skill_body
                    effective_user_message = (
                        f"Command: /{parsed.command_name}\n"
                        f"Command args: {parsed.raw_args}\n\n"
                        f"Selected skill instructions:\n{cmd_result.skill_body}"
                    )
                elif not cmd_result.handled:
                    error_text = cmd_result.error or "Unknown command"
                    self._record_conversation_turn(
                        runtime=runtime,
                        request=request,
                        turn_id=turn_id,
                        user_message=request.user_message,
                        assistant_message=error_text,
                    )
                    return {
                        "tenant": {
                            "tenant_id": request.tenant_id,
                            "workspace_root": str(runtime.context.workspace_root),
                            "db_path": str(runtime.context.db_path),
                        },
                        "turn": {
                            "session_id": request.session_id,
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "capability_source": "n/a",
                            "profile": request.profile.value,
                            "mode": "command_error",
                            "project_id": request.project_id,
                            "task_id": request.task_id,
                        },
                        "assistant": {
                            "text": error_text,
                            "provider": "command_router",
                            "usage": None,
                        },
                        "memory": {"pending_approvals": runtime.memory.pending_approvals(request.tenant_id, request.user_id)},
                        "identity": {
                            "profile": runtime.identity.get_profile(request.tenant_id, request.user_id),
                            "newly_applied_signals": [],
                            "pending_signals": runtime.identity.list_pending_signals(request.tenant_id, request.user_id),
                        },
                        "artifacts": [],
                    }

        if self.config.skill_nl_router_enabled:
            intent = parse_skill_nl_intent(request.user_message)
            if intent is not None:
                try:
                    if intent.name == "catalog_list":
                        rows = self.list_skill_catalog(
                            tenant_id=request.tenant_id,
                            workspace_root=str(runtime.context.workspace_root),
                            source=intent.source,
                            limit=intent.limit or 50,
                        )
                        payload = {"intent": intent.name, "skills": rows}
                    elif intent.name == "trust_get":
                        payload = {
                            "intent": intent.name,
                            "source_trust": self.get_skill_source_trust(
                                tenant_id=request.tenant_id,
                                workspace_root=str(runtime.context.workspace_root),
                            ),
                        }
                    elif intent.name == "trust_set":
                        if not intent.source or not intent.trust_mode:
                            raise ValueError("missing source or trust mode")
                        payload = {
                            "intent": intent.name,
                            "source_trust": self.set_skill_source_trust(
                                tenant_id=request.tenant_id,
                                source=intent.source,
                                trust_mode=intent.trust_mode,
                                workspace_root=str(runtime.context.workspace_root),
                            ),
                        }
                    elif intent.name == "install_request":
                        if not intent.source or not intent.skill_id:
                            raise ValueError("missing source or skill id")
                        install = self.create_skill_install_request(
                            tenant_id=request.tenant_id,
                            user_id=request.user_id,
                            source=intent.source,
                            skill_id=intent.skill_id,
                            session_id=request.session_id,
                            turn_id=turn_id,
                            workspace_root=str(runtime.context.workspace_root),
                            reason="requested_via_chat_nl",
                        )
                        payload = {
                            "intent": intent.name,
                            "install_request": install,
                            "next_step": "Approve with /approve tool:<approval_id>, then apply using /apply-install <request_id>.",
                        }
                    elif intent.name == "install_apply":
                        if not intent.request_id:
                            raise ValueError("missing request id")
                        payload = {
                            "intent": intent.name,
                            "result": self.execute_skill_install(
                                tenant_id=request.tenant_id,
                                request_id=intent.request_id,
                                workspace_root=str(runtime.context.workspace_root),
                            ),
                        }
                    elif intent.name == "install_requests_list":
                        payload = {
                            "intent": intent.name,
                            "install_requests": self.list_skill_install_requests(
                                tenant_id=request.tenant_id,
                                workspace_root=str(runtime.context.workspace_root),
                                status=None,
                                limit=100,
                            ),
                        }
                    elif intent.name == "diagnostics":
                        payload = {
                            "intent": intent.name,
                            "diagnostics": self.skill_diagnostics(
                                tenant_id=request.tenant_id,
                                workspace_root=str(runtime.context.workspace_root),
                            ),
                        }
                    elif intent.name == "telemetry":
                        payload = {
                            "intent": intent.name,
                            "telemetry": self.list_skill_telemetry(
                                tenant_id=request.tenant_id,
                                workspace_root=str(runtime.context.workspace_root),
                                limit=intent.limit or 50,
                            ),
                        }
                    else:
                        payload = {"intent": intent.name, "error": "unsupported_intent"}
                    payload_text = json.dumps(payload, indent=2, ensure_ascii=True)
                    self._record_conversation_turn(
                        runtime=runtime,
                        request=request,
                        turn_id=turn_id,
                        user_message=request.user_message,
                        assistant_message=payload_text,
                    )
                    return {
                        "tenant": {
                            "tenant_id": request.tenant_id,
                            "workspace_root": str(runtime.context.workspace_root),
                            "db_path": str(runtime.context.db_path),
                        },
                        "turn": {
                            "session_id": request.session_id,
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "capability_source": "n/a",
                            "profile": request.profile.value,
                            "mode": "skill_nl",
                            "project_id": request.project_id,
                            "task_id": request.task_id,
                        },
                        "assistant": {
                            "text": payload_text,
                            "provider": "skill_nl_router",
                            "usage": None,
                        },
                        "memory": {"pending_approvals": runtime.memory.pending_approvals(request.tenant_id, request.user_id)},
                        "identity": {
                            "profile": runtime.identity.get_profile(request.tenant_id, request.user_id),
                            "newly_applied_signals": [],
                            "pending_signals": runtime.identity.list_pending_signals(request.tenant_id, request.user_id),
                        },
                        "artifacts": [],
                    }
                except Exception as exc:
                    error_text = f"skill request could not be completed: {exc}"
                    self._record_conversation_turn(
                        runtime=runtime,
                        request=request,
                        turn_id=turn_id,
                        user_message=request.user_message,
                        assistant_message=error_text,
                    )
                    return {
                        "tenant": {
                            "tenant_id": request.tenant_id,
                            "workspace_root": str(runtime.context.workspace_root),
                            "db_path": str(runtime.context.db_path),
                        },
                        "turn": {
                            "session_id": request.session_id,
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "capability_source": "n/a",
                            "profile": request.profile.value,
                            "mode": "skill_nl_error",
                            "project_id": request.project_id,
                            "task_id": request.task_id,
                        },
                        "assistant": {
                            "text": error_text,
                            "provider": "skill_nl_router",
                            "usage": None,
                        },
                        "memory": {"pending_approvals": runtime.memory.pending_approvals(request.tenant_id, request.user_id)},
                        "identity": {
                            "profile": runtime.identity.get_profile(request.tenant_id, request.user_id),
                            "newly_applied_signals": [],
                            "pending_signals": runtime.identity.list_pending_signals(request.tenant_id, request.user_id),
                        },
                        "artifacts": [],
                    }

        capabilities, capability_source = self._capabilities(runtime, model_id)

        profile_before = runtime.identity.get_profile(request.tenant_id, request.user_id)
        pending_learning_approvals = runtime.memory.pending_approvals(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        )
        pending_tool_approvals = runtime.governance.list_pending_approvals(request.tenant_id)
        skill_diagnostics = runtime.skill_loader.diagnostics()
        generic_mode = (
            request.project_id is None
            and request.task_id is None
            and runtime.info.is_generic_query(effective_user_message)
        )

        search_query = (request.search_query or effective_user_message).strip()
        search_result: dict[str, Any]
        tool_results: list[dict[str, str]] = []
        web_snippets: list[dict[str, Any]] = []

        # When tools are disabled (e.g. orchestration phases), skip the
        # context search entirely — the user_message is a structured prompt
        # that would be invalid as a ripgrep pattern.
        if request.disable_tools:
            search_result = {
                "planId": str(uuid.uuid4()),
                "executedAt": datetime.now(timezone.utc).timestamp(),
                "pass": 0,
                "escalated": False,
                "executionMs": 0,
                "lowValueHitRatio": 0.0,
                "avgConfidence": 0.0,
                "commands": [],
                "results": [],
            }
        elif generic_mode:
            snippets = runtime.info.retrieve(search_query, limit=2)
            web_snippets = [
                {
                    "title": s.title,
                    "source": s.source_url,
                    "snippet": s.snippet,
                    "confidence": s.confidence,
                }
                for s in snippets
            ]
            search_result = {
                "planId": str(uuid.uuid4()),
                "executedAt": datetime.now(timezone.utc).timestamp(),
                "pass": 0,
                "escalated": False,
                "executionMs": 0,
                "lowValueHitRatio": 0.0,
                "avgConfidence": (sum(s["confidence"] for s in web_snippets) / len(web_snippets)) if web_snippets else 0.0,
                "commands": [],
                "results": [
                    {
                        "path": s["source"],
                        "lineStart": 0,
                        "lineEnd": 0,
                        "confidence": s["confidence"],
                        "snippet": s["snippet"],
                        "rationale": "generic_info_retrieval",
                    }
                    for s in web_snippets
                ],
            }
        else:
            search_pack = runtime.search.execute(
                SearchPlan(
                    query=search_query,
                    intent="broad_discovery",
                    scope=["."],
                    file_types=["py", "ts", "js", "md", "sql", "json"],
                    escalation_allowed=True,
                    escalation_mode="balanced",
                )
            )
            search_result = result_pack_to_dict(search_pack)
            tool_results = [
                {
                    "source": f"search://{hit.path}#L{hit.line_start}",
                    "text": hit.snippet,
                }
                for hit in search_pack.results[:8]
            ]

        recall = runtime.memory.recall(user_id=request.user_id, query=search_query, limit=8)

        # Unified peer identity: if we can resolve a being_id from the session,
        # also recall memories tagged with that being_id (cross-context access).
        # This replaces the old cross-namespace hack that used user_id prefixes.
        _being_id = resolve_being_id(request.session_id, request.user_id)
        if _being_id:
            try:
                _being_recall = runtime.memory.recall_by_being(
                    being_id=_being_id, query=search_query, limit=4,
                )
                # Merge being-scoped semantic/markdown into recall, dedup by memory_id
                _seen_ids = {m.get("memory_id") for m in recall.get("semantic", [])}
                for item in _being_recall.get("semantic", []):
                    if item.get("memory_id") not in _seen_ids:
                        recall["semantic"].append(item)
                        _seen_ids.add(item.get("memory_id"))
                _seen_note_ids = {m.get("note_id") for m in recall.get("markdown", [])}
                for item in _being_recall.get("markdown", []):
                    if item.get("note_id") not in _seen_note_ids:
                        recall["markdown"].append(item)
                        _seen_note_ids.add(item.get("note_id"))
            except Exception:
                pass  # non-critical — don't fail the turn

        procedural_memories = runtime.memory.recall_procedural(user_id=request.user_id, query=search_query, limit=5)
        # Orchestration/subtask sessions get stripped replay (text only,
        # no tool_use/tool_result blocks) to give beings continuity during
        # revision rounds without risking API errors from stale tool blocks.
        _is_orch_session = (
            "subtask:" in request.session_id
            or "orchestration:" in request.session_id
        )
        if _is_orch_session:
            raw_turns = runtime.memory.get_recent_turns(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                user_id=request.user_id,
                limit=3,  # Fewer turns for subtask context — keep it focused
            )
            recent_turn_messages = _strip_tool_blocks(raw_turns)
        else:
            recent_turn_messages = runtime.memory.get_recent_turns(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                user_id=request.user_id,
                limit=5,
            )
        session_summary = runtime.memory.get_session_summary(
            tenant_id=request.tenant_id,
            session_id=request.session_id,
        )
        semantic_candidates = self._semantic_candidates(recall)
        for snippet in web_snippets:
            semantic_candidates.append(
                {
                    "text": snippet["snippet"],
                    "source": snippet["source"],
                    "recency_label": datetime.now(timezone.utc).isoformat(),
                    "contradictory": False,
                }
            )
        procedural_candidates = [
            {
                "text": item["content"],
                "source": f"memory://procedural/{item['id']}",
                "recency_label": item["updated_at"],
            }
            for item in procedural_memories
        ]
        if not procedural_candidates:
            procedural_candidates = [{"text": "Use local-first search then escalate only on low confidence."}]

        task_state = {
            "text": "Respond as a chat assistant while preserving memory and auditability.",
        }
        project_block = None
        task_block = None
        if request.project_id:
            try:
                project_block = runtime.projects.get_project(request.tenant_id, request.project_id)
            except ValueError:
                project_block = None
        if request.task_id:
            try:
                task_block = runtime.projects.get_task(request.tenant_id, request.task_id)
            except ValueError:
                task_block = None

        if project_block:
            task_state["text"] += f" Active project={project_block['name']}({project_block['project_id']})."
        if task_block:
            task_state["text"] += f" Active task={task_block['title']}({task_block['task_id']}) status={task_block['status']}."

        system_prefix_parts: list[str] = []
        # For casual chat, only load core identity (SOUL + IDENTITY).
        # Heavy files (MISSION, VISION, FORMULA, PRIORITIES, KNOWLEDGE, etc.)
        # are only injected for task_execution/planning profiles.
        _needs_deep_context = request.profile in (TurnProfile.TASK_EXECUTION, TurnProfile.PLANNING)
        if runtime.soul is not None:
            if runtime.soul.raw_soul_text.strip():
                system_prefix_parts.append("<soul>\n" + runtime.soul.raw_soul_text.strip() + "\n</soul>")
            if runtime.soul.raw_identity_text.strip():
                system_prefix_parts.append("<identity>\n" + runtime.soul.raw_identity_text.strip() + "\n</identity>")
            if _needs_deep_context:
                mission_block: list[str] = []
                if runtime.soul.mission_text and runtime.soul.mission_text.strip():
                    mission_block.append("<mission>\n" + runtime.soul.mission_text.strip() + "\n</mission>")
                if runtime.soul.vision_text and runtime.soul.vision_text.strip():
                    mission_block.append("<vision>\n" + runtime.soul.vision_text.strip() + "\n</vision>")
                if mission_block:
                    system_prefix_parts.append("\n".join(mission_block))
                if runtime.soul.formula_text and runtime.soul.formula_text.strip():
                    system_prefix_parts.append("<formula>\n" + runtime.soul.formula_text.strip()[:12000] + "\n</formula>")
                if runtime.soul.priorities_text and runtime.soul.priorities_text.strip():
                    system_prefix_parts.append("<priorities>\n" + runtime.soul.priorities_text.strip()[:8000] + "\n</priorities>")
                if runtime.soul.knowledge_text and runtime.soul.knowledge_text.strip():
                    system_prefix_parts.append(
                        "<knowledge editable=\"true\">\n"
                        + runtime.soul.knowledge_text.strip()[:4000]
                        + "\n</knowledge>"
                    )
                if runtime.soul.team_context_text and runtime.soul.team_context_text.strip():
                    system_prefix_parts.append(
                        "<team-context readonly=\"true\">\n"
                        + runtime.soul.team_context_text.strip()[:3000]
                        + "\n</team-context>"
                    )
            if (request.include_representation
                    and runtime.soul.representation_text
                    and runtime.soul.representation_text.strip()):
                system_prefix_parts.append(
                    '<representation readonly="true">\n'
                    + runtime.soul.representation_text.strip()[:3000]
                    + '\n</representation>'
                )

        if runtime.soul is not None:
            # Identity comes from workspace SoulConfig — nothing else
            system_prefix_parts.append(
                f"You are {runtime.soul.name}. "
                "Use cited evidence, respect explicit constraints, "
                "and prefer local-first retrieval before broad assumptions."
            )
        else:
            # No SoulConfig found — default to SAI identity
            system_prefix_parts.append(
                "You are SAI (Super Actualized Intelligence), the Prime Orchestrator of the ACT-I ecosystem. "
                "Use cited evidence, respect explicit constraints, "
                "and prefer local-first retrieval before broad assumptions."
            )
        skill_index = runtime.skill_disclosure.format_skill_index_xml(runtime.skill_loader.snapshot())
        system_prefix_parts.append(
            "Answer directly and cite local evidence when available. "
            "If the user asks to create or modify a skill, use skill_create or skill_update tools.\n\n"
            + skill_index
        )
        if selected_skill_context:
            system_prefix_parts.append(f"Use selected skill instructions:\n{selected_skill_context}")
        system_prompt = "\n\n".join(system_prefix_parts)

        system_contract = (
            "Use cited evidence, respect explicit constraints, "
            "and prefer local-first retrieval before broad assumptions."
        )

        working_memory_entries: list[dict[str, str]] = [
            {"text": "Current goal: answer user and capture durable learnings."},
            {"text": f"pending_learning_approvals={len(pending_learning_approvals)}"},
            {"text": f"pending_tool_approvals={len(pending_tool_approvals)}"},
            {"text": f"skill_parse_warnings={sum(len(v) for v in skill_diagnostics.values())}"},
        ]

        context_result = runtime.context_engine.assemble(
            profile=request.profile,
            model_context_length=capabilities.context_length,
            system_contract=system_contract,
            user_message=effective_user_message,
            inputs={
                "explicit_user_constraints": ["Do not fabricate sources"],
                "task_state": task_state,
                "working_memory": working_memory_entries,
                "world_state": [
                    {"text": f"workspace_root={runtime.context.workspace_root}"},
                    {"text": f"persona_summary={profile_before['persona_summary']}"},
                ],
                "semantic_candidates": semantic_candidates,
                "recent_history": [
                    {"text": f"session_id={request.session_id}"},
                    (
                        {"text": f"session_summary={session_summary['summary_text']}"}
                        if session_summary is not None
                        else {"text": "session_summary=None"}
                    ),
                ],
                "procedural_candidates": procedural_candidates,
                "pending_predictions": [{"text": "User may request artifacts or code changes next."}],
                "tool_results": tool_results,
            },
        )

        context_budget = calculate_budget(capabilities.context_length)
        total_available_input_tokens = int(context_budget.available_input_tokens)
        replay_hard_cap_tokens = int(total_available_input_tokens * self.config.replay_history_budget_fraction)
        replay_remaining_tokens = max(0, total_available_input_tokens - int(context_result.final_input_tokens))
        replay_token_budget = max(0, min(replay_hard_cap_tokens, replay_remaining_tokens))
        replay_messages = self._cap_recent_turn_messages(
            recent_turn_messages=recent_turn_messages,
            replay_token_budget=replay_token_budget,
        )

        assistant_usage: dict[str, int] | None
        assistant_text: str
        loop_iterations = 1
        loop_tool_calls: list[dict[str, Any]] = []
        loop_stopped_reason: str | None = None
        loop_duration_ms = 0
        loop_estimated_cost_usd = 0.0
        loop_budget_exhausted = False
        cascade_stopped_runs: list[str] = []
        rescue_info: dict[str, Any] = {"method": "disabled"}
        adaptation_turn_count = 0
        adaptation_correction: dict[str, Any] = {"action": "none", "reasons": []}
        adaptation_evaluation: dict[str, Any] | None = None
        if self.config.agentic_loop_enabled:
            loop_started_at = datetime.now(timezone.utc)
            rescue: WorkspaceRescue | None = None
            if self.config.rescue_enabled:
                rescue = WorkspaceRescue(runtime.context.workspace_root)
                rescue_info = rescue.snapshot()
            runtime_policy = runtime.adaptation.get_policy("default")
            runtime_policy_values = (
                dict(runtime_policy.get("policy") or {})
                if runtime_policy is not None and isinstance(runtime_policy.get("policy"), dict)
                else {}
            )
            effective_max_iterations = self._policy_int(
                runtime_policy_values,
                key="max_loop_iterations",
                default=self.config.max_loop_iterations,
                min_value=1,
            )
            if request.max_loop_iterations is not None:
                effective_max_iterations = min(
                    effective_max_iterations,
                    self._policy_int(
                        policy_values={"requested": request.max_loop_iterations},
                        key="requested",
                        default=effective_max_iterations,
                        min_value=1,
                    ),
                )
            effective_loop_detection = self._policy_int(
                runtime_policy_values,
                key="loop_detection_window",
                default=self.config.loop_detection_window,
                min_value=1,
            )
            effective_budget_limit = self._policy_float(
                runtime_policy_values,
                key="budget_limit_usd",
                default=self.config.budget_limit_usd,
                min_value=0.01,
            )
            effective_budget_stop_pct = self._policy_float(
                runtime_policy_values,
                key="budget_hard_stop_pct",
                default=self.config.budget_hard_stop_pct,
                min_value=0.01,
            )
            if effective_budget_stop_pct > 1.0:
                effective_budget_stop_pct = 1.0
            effective_parallel_reads = self._policy_bool(
                runtime_policy_values,
                key="parallel_read_tools",
                default=self.config.parallel_read_tools,
            )
            resolved_policy = runtime.policy_pipeline.resolve(
                ToolPolicyContext(
                    profile=self.config.tool_profile,
                    tenant_id=request.tenant_id,
                    provider_name=self.provider.provider_name,
                ),
                available_tools=runtime.tool_executor.known_tool_names(),
            )
            # ── Per-being tool filtering (ACT-I Phase 2) ──────────────
            # Resolve tool_profile from SisterConfig if available, else fall back to tenant_id
            _sister_cfg = runtime.sisters.get_sister_by_tenant(request.tenant_id) if runtime.sisters else None
            being_denied = get_denied_tools(
                runtime.tool_executor.known_tool_names(),
                profile_name=_sister_cfg.tool_profile if _sister_cfg else None,
                tenant_id=request.tenant_id,
            )
            if being_denied:
                from dataclasses import replace
                merged_denied = resolved_policy.denied_tools | being_denied
                merged_allowed = resolved_policy.allowed_tools
                if merged_allowed is not None:
                    merged_allowed = merged_allowed - being_denied
                resolved_policy = replace(
                    resolved_policy,
                    denied_tools=merged_denied,
                    allowed_tools=merged_allowed,
                    source_layers=resolved_policy.source_layers + ("being_profile",),
                )
            tool_context = ToolContext(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                turn_id=turn_id,
                user_id=request.user_id,
                workspace_root=runtime.context.workspace_root,
                db=runtime.db,
                guard_path=lambda p: self.registry.guard_path(runtime.context, p),
            )
            tool_format = "anthropic" if self.provider.provider_name == "anthropic" else "openai"
            # ── Log Point B: handle_turn receives orchestration request ──
            if "subtask:" in request.session_id or "orchestration:" in request.session_id:
                tool_names = [] if request.disable_tools else runtime.tool_executor.known_tool_names()
                logger.debug(f"[ORCH] ── Log Point B: handle_turn called ──")
                logger.debug(f"[ORCH] handle_turn for {request.tenant_id}/{request.session_id}")
                logger.debug(f"[ORCH] Model: {model_id}")
                logger.debug(f"[ORCH] Provider: {self.provider.provider_name} base_url={getattr(self.provider, 'api_base', 'N/A')}")
                logger.debug(f"[ORCH] Tools enabled: {tool_names[:20]}{'...' if len(tool_names) > 20 else ''}")
                logger.debug(f"[ORCH] disable_tools={request.disable_tools}")
                logger.debug(f"[ORCH] System prompt length: {len(system_prompt)} chars")

            loop = AgenticLoop(
                provider=self.provider,
                tool_executor=runtime.tool_executor,
                config=LoopConfig(
                    max_iterations=effective_max_iterations,
                    loop_detection_window=effective_loop_detection,
                    budget_limit_usd=effective_budget_limit,
                    budget_hard_stop_pct=effective_budget_stop_pct,
                    parallel_read_tools=effective_parallel_reads,
                ),
            )
            loop_result = loop.run(
                initial_messages=[
                    ChatMessage(role="system", content=system_prompt, cache_control={"type": "ephemeral"}),
                    *replay_messages,
                    ChatMessage(role="user", content=context_result.context_text),
                ],
                tool_schemas=[] if request.disable_tools else runtime.tool_executor.available_tool_schemas(resolved_policy, format=tool_format),
                context=tool_context,
                resolved_policy=resolved_policy,
                model_id=model_id,
                tool_format=tool_format,
                on_iteration=request.on_iteration,
            )
            assistant_text = loop_result.final_text
            assistant_usage = {
                "input_tokens": loop_result.total_input_tokens,
                "output_tokens": loop_result.total_output_tokens,
                "total_tokens": loop_result.total_input_tokens + loop_result.total_output_tokens,
            }
            loop_duration_ms = int((datetime.now(timezone.utc) - loop_started_at).total_seconds() * 1000)
            loop_iterations = loop_result.iterations
            loop_tool_calls = [item.as_dict() for item in loop_result.tool_calls]
            loop_stopped_reason = loop_result.stopped_reason
            loop_estimated_cost_usd = loop_result.estimated_cost_usd
            loop_budget_exhausted = loop_result.budget_exhausted
            if loop_stopped_reason in {"budget_exhausted", "max_iterations"}:
                cascade_stopped_runs = runtime.protocol.cascade_stop_session(
                    tenant_id=request.tenant_id,
                    session_id=request.session_id,
                    reason=f"parent_loop_{loop_stopped_reason}",
                )
            if rescue is not None and loop_stopped_reason not in {"budget_exhausted", "error"}:
                rescue.cleanup_ref()
        else:
            response = self.provider.generate(
                model=model_id,
                messages=[
                    ChatMessage(role="system", content=system_prompt, cache_control={"type": "ephemeral"}),
                    *replay_messages,
                    ChatMessage(role="user", content=context_result.context_text),
                ],
            )
            assistant_text = response.text
            assistant_usage = response.usage

        procedural_learning: dict[str, Any] | None = None
        if loop_tool_calls:
            ordered_tools: list[str] = []
            statuses: list[str] = []
            for item in loop_tool_calls:
                tool_name = str(item.get("tool_name") or item.get("tool") or "").strip()
                status = str(item.get("status") or "").strip().lower()
                if tool_name:
                    ordered_tools.append(tool_name)
                if status:
                    statuses.append(status)
            if ordered_tools:
                chain_signature = ",".join(ordered_tools)
                digest = hashlib.sha1(chain_signature.encode("utf-8")).hexdigest()[:12]
                strategy_key = f"toolchain_{digest}"
                strategy_content = (
                    f"Use tool chain: {chain_signature}. "
                    f"Observed stop_reason={loop_stopped_reason or 'completed'}."
                )
                strategy_success = bool(statuses) and all(s == "executed" for s in statuses)
                strategy_memory_id = runtime.memory.learn_procedural(
                    user_id=request.user_id,
                    strategy_key=strategy_key,
                    content=strategy_content,
                    success=strategy_success,
                    being_id=_being_id_for_write,
                )
                procedural_learning = {
                    "memory_id": strategy_memory_id,
                    "strategy_key": strategy_key,
                    "success": strategy_success,
                    "tool_chain": ordered_tools,
                }

        markdown_artifact = None
        if self._should_create_markdown_artifact(effective_user_message):
            markdown_artifact = runtime.artifacts.create_text_artifact(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                turn_id=turn_id,
                project_id=request.project_id,
                task_id=request.task_id,
                artifact_type="markdown",
                title="assistant-response",
                content=assistant_text,
            )

        extracted_code = self._extract_first_code_block(assistant_text)
        code_artifact = None
        if extracted_code:
            code_artifact = runtime.artifacts.create_text_artifact(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                turn_id=turn_id,
                project_id=request.project_id,
                task_id=request.task_id,
                artifact_type="code",
                title="assistant-code-snippet",
                content=extracted_code,
            )

        note = runtime.memory.append_working_note(
            user_id=request.user_id,
            session_id=request.session_id,
            title=f"turn-{turn_id[:8]}",
            content=f"User: {effective_user_message}\n\nAssistant: {assistant_text}",
            tags=["chat", "runtime", "generic_info" if generic_mode else "project_mode"],
            confidence=1.0,
            being_id=_being_id_for_write,
        )
        turn_number = runtime.memory.record_turn(
            tenant_id=request.tenant_id,
            session_id=request.session_id,
            turn_id=turn_id,
            user_id=request.user_id,
            user_message=effective_user_message,
            assistant_message=assistant_text,
        )
        summary_recent_window = 3
        if turn_number % 5 == 0 and turn_number > summary_recent_window:
            previous_summary = runtime.memory.get_session_summary(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
            )
            covered_turn = int(previous_summary["covers_through_turn"]) if previous_summary is not None else 0
            turns_to_summarize = runtime.memory.get_turns_for_summary(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                user_id=request.user_id,
                covers_through_turn=covered_turn,
                recent_window=summary_recent_window,
                limit=200,
            )
            if turns_to_summarize:
                merged_summary = runtime.memory.generate_session_summary(
                    turns=turns_to_summarize,
                    provider=self.provider,
                    model_id=model_id,
                    existing_summary=(previous_summary["summary_text"] if previous_summary else None),
                )
                if merged_summary.strip():
                    runtime.memory.update_session_summary(
                        tenant_id=request.tenant_id,
                        session_id=request.session_id,
                        user_id=request.user_id,
                        summary_text=merged_summary,
                        covers_through_turn=int(turns_to_summarize[-1]["turn_number"]),
                    )

        learning_signal = self._learning_signal(effective_user_message)
        decision = None
        if learning_signal is not None:
            learning_key, learning_content, confidence, reason = learning_signal
            decision = runtime.memory.learn_semantic(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                memory_key=learning_key,
                content=learning_content,
                confidence=confidence,
                evidence_refs=[note["note_id"]],
                reason=reason,
                being_id=_being_id_for_write,
            )

        identity_update = runtime.identity.ingest_turn(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            text=effective_user_message,
            source_ref=note["note_id"],
        )

        now = datetime.now(timezone.utc)
        period_start = (now - timedelta(minutes=5)).isoformat()
        period_end = now.isoformat()
        runtime.adaptation.ingest_search_metric(
            escalated=bool(search_result.get("escalated", False)),
            precision_at_k=float(search_result.get("avgConfidence", 0.0)),
            execution_ms=int(search_result.get("executionMs", 0)),
            created_at=period_start,
        )
        rollup = runtime.adaptation.aggregate_period(period_start=period_start, period_end=period_end)
        adaptation_turn_count = runtime.adaptation.ingest_turn_metrics(request.session_id)
        if self.config.adaptation_auto_correct and adaptation_turn_count % self.config.adaptation_metrics_interval == 0:
            adaptation_correction = runtime.adaptation.check_and_correct("default")
        if adaptation_turn_count % self.config.adaptation_llm_eval_interval == 0:
            try:
                evaluator = SelfEvaluator(self.provider, runtime.db)
                adaptation_evaluation = evaluator.evaluate(
                    tenant_id=request.tenant_id,
                    session_id=request.session_id,
                    model_id=model_id,
                )
                suggested_updates = adaptation_evaluation.get("policy_updates")
                if self.config.adaptation_auto_correct and isinstance(suggested_updates, dict) and suggested_updates:
                    current_policy = runtime.adaptation.get_policy("default")
                    current_values = (
                        dict(current_policy.get("policy") or {})
                        if current_policy is not None and isinstance(current_policy.get("policy"), dict)
                        else {}
                    )
                    merged = dict(current_values)
                    merged.update(suggested_updates)
                    runtime.adaptation.update_policy(
                        policy_name="default",
                        new_policy=merged,
                        reason="llm_self_evaluation",
                    )
            except Exception as exc:
                adaptation_evaluation = {
                    "error": str(exc),
                    "evaluated_loops": 0,
                    "policy_updates": {},
                    "recommendations": [],
                }
        runtime.db.execute(
            """
            INSERT INTO loop_executions (
              id, tenant_id, session_id, turn_id, iterations, tool_calls_json, stopped_reason,
              total_input_tokens, total_output_tokens, duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                request.tenant_id,
                request.session_id,
                turn_id,
                loop_iterations,
                json.dumps(loop_tool_calls, separators=(",", ":")),
                loop_stopped_reason,
                int((assistant_usage or {}).get("input_tokens") or 0),
                int((assistant_usage or {}).get("output_tokens") or 0),
                loop_duration_ms,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        runtime.db.commit()

        artifacts = []
        if markdown_artifact is not None:
            artifacts.append(markdown_artifact)
        if code_artifact is not None:
            artifacts.append(code_artifact)

        return {
            "tenant": {
                "tenant_id": request.tenant_id,
                "workspace_root": str(runtime.context.workspace_root),
                "db_path": str(runtime.context.db_path),
            },
            "turn": {
                "session_id": request.session_id,
                "turn_id": turn_id,
                "model_id": model_id,
                "capability_source": capability_source,
                "profile": request.profile.value,
                "mode": "generic_info" if generic_mode else "project",
                "project_id": request.project_id,
                "task_id": request.task_id,
            },
            "codeintel": runtime.codeintel.availability(),
            "search": search_result,
            "context": {
                "final_input_tokens": context_result.final_input_tokens,
                "compressed": context_result.compressed,
                "included_sections": context_result.included_sections,
                "dropped_sections": context_result.dropped_sections,
                "compression_summary": context_result.compression_summary,
            },
            "assistant": {
                "text": assistant_text,
                "provider": self.provider.provider_name,
                "usage": assistant_usage,
                "loop_iterations": loop_iterations,
                "tool_calls": loop_tool_calls,
                "stopped_reason": loop_stopped_reason,
                "estimated_cost_usd": loop_estimated_cost_usd,
                "budget_exhausted": loop_budget_exhausted,
            },
            "memory": {
                "note": note,
                "learning": (
                    {
                        "update_id": decision.update_id,
                        "status": decision.status,
                        "confidence": decision.confidence,
                        "memory_id": decision.memory_id,
                    }
                    if decision is not None
                    else {
                        "update_id": None,
                        "status": "skipped",
                        "confidence": 0.0,
                        "memory_id": None,
                    }
                ),
                "procedural_learning": procedural_learning,
                "pending_approvals": pending_learning_approvals,
            },
            "approvals": {
                "pending_learning_approvals": pending_learning_approvals,
                "pending_tool_approvals": pending_tool_approvals,
                "pending_total": len(pending_learning_approvals) + len(pending_tool_approvals),
            },
            "skills": {
                "parse_diagnostics": skill_diagnostics,
                "telemetry_enabled": self.config.skills_telemetry_enabled,
            },
            "identity": {
                "profile": identity_update["profile"],
                "newly_applied_signals": identity_update["applied"],
                "pending_signals": runtime.identity.list_pending_signals(request.tenant_id, request.user_id),
            },
            "artifacts": [self._artifact_dict(a) for a in artifacts],
            "adaptation": {
                "retrieval_precision_at_k": rollup.retrieval_precision_at_k,
                "search_escalation_rate": rollup.search_escalation_rate,
                "subagent_success_rate": rollup.subagent_success_rate,
                "subagent_p95_latency_ms": rollup.subagent_p95_latency_ms,
                "turn_count": adaptation_turn_count,
                "correction": adaptation_correction,
                "self_evaluation": adaptation_evaluation,
            },
            "rescue": rescue_info,
            "subagents": {
                "cascade_stopped_runs": cascade_stopped_runs,
            },
        }

    def invoke_code_tool(
        self,
        tenant_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        workspace_root: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        policy = runtime.policy_pipeline.resolve(
            ToolPolicyContext(
                profile=self.config.tool_profile,
                tenant_id=tenant_id,
                provider_name=self.provider.provider_name,
            ),
            available_tools=runtime.tool_executor.known_tool_names(),
        )
        context = ToolContext(
            tenant_id=tenant_id,
            session_id=session_id or "session-tool",
            turn_id=turn_id or str(uuid.uuid4()),
            user_id="user-tool",
            workspace_root=runtime.context.workspace_root,
            db=runtime.db,
            guard_path=lambda p: self.registry.guard_path(runtime.context, p),
        )
        outcome = runtime.tool_executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            policy=policy,
            confidence=confidence,
        )
        payload = {
            "status": outcome.status,
            "tool_name": outcome.tool_name,
            "risk_class": outcome.risk_class,
            "payload": outcome.output,
            "duration_ms": outcome.duration_ms,
        }
        if outcome.status == "approval_required":
            if "approval_id" in outcome.output:
                payload["approval_id"] = outcome.output["approval_id"]
            if "reason" in outcome.output:
                payload["reason"] = outcome.output["reason"]
        if outcome.status == "denied" and "reason" in outcome.output:
            payload["reason"] = outcome.output["reason"]
        return payload

    def list_pending_approvals(self, tenant_id: str, workspace_root: str | None = None) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.governance.list_pending_approvals(tenant_id)

    def list_pending_learning_approvals(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.memory.pending_approvals(tenant_id=tenant_id, user_id=user_id)

    def decide_approval(
        self,
        tenant_id: str,
        approval_id: str,
        approved: bool,
        decided_by: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.governance.decide_approval(tenant_id, approval_id, approved, decided_by)

    def register_skill(
        self,
        tenant_id: str,
        manifest: dict[str, Any],
        status: str = "active",
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        skill = runtime.skills_registry.register_skill(tenant_id, manifest, status=status)
        return {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "status": skill.status,
            "name": skill.name,
            "description": skill.description,
        }

    def list_skills(self, tenant_id: str, workspace_root: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        skills = runtime.skills_registry.list_skills(tenant_id, status=status)
        return [
            {
                "skill_id": s.skill_id,
                "version": s.version,
                "status": s.status,
                "name": s.name,
                "description": s.description,
                "source": s.source,
                "source_path": s.source_path,
                "intent_tags": s.manifest.get("intent_tags") or [],
                "risk_level": s.manifest.get("risk_level"),
            }
            for s in skills
        ]

    def skill_diagnostics(self, tenant_id: str, workspace_root: str | None = None) -> dict[str, list[str]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skill_loader.diagnostics()

    def list_skill_catalog(
        self,
        tenant_id: str,
        workspace_root: str | None = None,
        source: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return [item.__dict__ for item in runtime.skills_ecosystem.list_catalog_skills(source=source, limit=limit)]

    def get_skill_source_trust(self, tenant_id: str, workspace_root: str | None = None) -> dict[str, str]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skills_ecosystem.trust_policy(tenant_id)

    def set_skill_source_trust(
        self,
        tenant_id: str,
        source: str,
        trust_mode: str,
        workspace_root: str | None = None,
    ) -> dict[str, str]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skills_ecosystem.set_trust_override(tenant_id=tenant_id, source=source, trust_mode=trust_mode)

    def create_skill_install_request(
        self,
        tenant_id: str,
        user_id: str,
        source: str,
        skill_id: str,
        session_id: str | None = None,
        turn_id: str | None = None,
        workspace_root: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        req = runtime.skills_ecosystem.create_install_request(
            tenant_id=tenant_id,
            user_id=user_id,
            source=source,
            skill_id=skill_id,
            workspace_root=str(runtime.context.workspace_root),
            session_id=session_id,
            turn_id=turn_id,
            reason=reason,
        )
        return req.__dict__

    def list_skill_install_requests(
        self,
        tenant_id: str,
        workspace_root: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return [item.__dict__ for item in runtime.skills_ecosystem.list_install_requests(tenant_id, status=status, limit=limit)]

    def execute_skill_install(
        self,
        tenant_id: str,
        request_id: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skills_ecosystem.execute_install(
            tenant_id=tenant_id,
            request_id=request_id,
            workspace_root=str(runtime.context.workspace_root),
        )

    def list_skill_telemetry(
        self,
        tenant_id: str,
        workspace_root: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skills_ecosystem.list_telemetry(tenant_id=tenant_id, limit=limit)

    def list_commands(self, tenant_id: str, workspace_root: str | None = None) -> list[dict[str, str]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        runtime.command_router.rebuild_command_map(runtime.skill_loader.snapshot())
        return runtime.command_router.available_commands()

    def execute_command(
        self,
        tenant_id: str,
        session_id: str,
        user_id: str,
        command_text: str,
        workspace_root: str | None = None,
        model_id: str | None = None,
        profile: TurnProfile = TurnProfile.CHAT,
    ) -> dict[str, Any]:
        return self.handle_turn(
            TurnRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=user_id,
                user_message=command_text,
                model_id=model_id,
                profile=profile,
                workspace_root=workspace_root,
            )
        )

    def execute_skill(
        self,
        tenant_id: str,
        skill_id: str,
        inputs: dict[str, Any],
        workspace_root: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)

        def invoker(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
            return self.invoke_code_tool(
                tenant_id=tenant_id,
                tool_name=tool_name,
                arguments=tool_args,
                workspace_root=workspace_root,
                session_id=session_id,
                turn_id=turn_id,
                confidence=confidence,
            )

        result = runtime.skills_engine.execute(
            tenant_id=tenant_id,
            skill_id=skill_id,
            inputs=inputs,
            session_id=session_id,
            turn_id=turn_id,
            tool_invoker=invoker,
        )
        return {
            "execution_id": result.execution_id,
            "status": result.status,
            "output": result.output,
            "tool_calls": result.tool_calls,
            "error_detail": result.error_detail,
            "duration_ms": result.duration_ms,
        }

    def list_skill_executions(self, tenant_id: str, workspace_root: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.skills_registry.list_executions(tenant_id=tenant_id, limit=limit)

    def create_project(
        self,
        tenant_id: str,
        name: str,
        workspace_root: str,
        description: str | None = None,
        project_id: str | None = None,
        status: str = "active",
        runtime_workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, runtime_workspace_root)
        return runtime.projects.create_project(
            tenant_id=tenant_id,
            name=name,
            workspace_root=workspace_root,
            description=description,
            project_id=project_id,
            status=status,
        )

    def list_projects(self, tenant_id: str, workspace_root: str | None = None) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.projects.list_projects(tenant_id)

    def create_task(
        self,
        tenant_id: str,
        project_id: str,
        title: str,
        description: str | None = None,
        task_id: str | None = None,
        status: str = "todo",
        priority: str = "normal",
        owner_agent_id: str | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.projects.create_task(
            tenant_id=tenant_id,
            project_id=project_id,
            title=title,
            description=description,
            task_id=task_id,
            status=status,
            priority=priority,
            owner_agent_id=owner_agent_id,
        )

    def list_tasks(
        self,
        tenant_id: str,
        project_id: str | None = None,
        status: str | None = None,
        workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.projects.list_tasks(tenant_id, project_id=project_id, status=status)

    def update_task(
        self,
        tenant_id: str,
        task_id: str,
        status: str | None = None,
        priority: str | None = None,
        owner_agent_id: str | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.projects.update_task(
            tenant_id=tenant_id,
            task_id=task_id,
            status=status,
            priority=priority,
            owner_agent_id=owner_agent_id,
        )

    # ── Team Manager delegation ──

    def tm_create_graph(
        self, tenant_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.create_graph(tenant_id=tenant_id, **kwargs)

    def tm_get_graph(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any] | None:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.get_graph(tenant_id=tenant_id, graph_id=graph_id)

    def tm_list_graphs(
        self, tenant_id: str, workspace_root: str | None = None, workspace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_graphs(tenant_id=tenant_id, workspace_id=workspace_id)

    def tm_update_graph(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.update_graph(tenant_id=tenant_id, graph_id=graph_id, **kwargs)

    def tm_delete_graph(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.delete_graph(tenant_id=tenant_id, graph_id=graph_id)

    def tm_add_node(
        self, tenant_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.add_node(tenant_id=tenant_id, **kwargs)

    def tm_list_nodes(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None, kind: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_nodes(tenant_id=tenant_id, graph_id=graph_id, kind=kind)

    def tm_update_node(
        self, tenant_id: str, node_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.update_node(tenant_id=tenant_id, node_id=node_id, **kwargs)

    def tm_delete_node(
        self, tenant_id: str, node_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.delete_node(tenant_id=tenant_id, node_id=node_id)

    def tm_add_edge(
        self, tenant_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.add_edge(tenant_id=tenant_id, **kwargs)

    def tm_list_edges(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None, edge_type: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_edges(tenant_id=tenant_id, graph_id=graph_id, edge_type=edge_type)

    def tm_delete_edge(
        self, tenant_id: str, edge_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.delete_edge(tenant_id=tenant_id, edge_id=edge_id)

    def tm_validate_graph(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.validate_graph(tenant_id=tenant_id, graph_id=graph_id)

    def tm_deploy_graph(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.deploy_graph(tenant_id=tenant_id, graph_id=graph_id)

    def tm_get_deployment(
        self, tenant_id: str, deployment_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any] | None:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)

    def tm_list_deployments(
        self, tenant_id: str, graph_id: str | None = None, workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_deployments(tenant_id=tenant_id, graph_id=graph_id)

    def tm_cancel_deployment(
        self, tenant_id: str, deployment_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.cancel_deployment(tenant_id=tenant_id, deployment_id=deployment_id)

    def tm_generate_primer(
        self, tenant_id: str, graph_id: str, node_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.generate_deploy_primer(
            tenant_id=tenant_id, graph_id=graph_id, node_id=node_id,
        )

    # ── Team Manager schedule delegation ──

    def tm_create_schedule(
        self, tenant_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.create_schedule(tenant_id=tenant_id, **kwargs)

    def tm_list_schedules(
        self, tenant_id: str, graph_id: str | None = None, workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_schedules(tenant_id=tenant_id, graph_id=graph_id)

    def tm_update_schedule(
        self, tenant_id: str, schedule_id: str, workspace_root: str | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.update_schedule(tenant_id=tenant_id, schedule_id=schedule_id, **kwargs)

    def tm_delete_schedule(
        self, tenant_id: str, schedule_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.delete_schedule(tenant_id=tenant_id, schedule_id=schedule_id)

    def tm_toggle_schedule(
        self, tenant_id: str, schedule_id: str, enabled: bool, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.toggle_schedule(tenant_id=tenant_id, schedule_id=schedule_id, enabled=enabled)

    # ── Variables ──

    def tm_set_variable(
        self, tenant_id: str, graph_id: str, key: str,
        value: str = "", var_type: str = "string",
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.set_variable(
            tenant_id=tenant_id, graph_id=graph_id, key=key, value=value, var_type=var_type,
        )

    def tm_list_variables(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_variables(tenant_id=tenant_id, graph_id=graph_id)

    def tm_delete_variable(
        self, tenant_id: str, graph_id: str, key: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.delete_variable(tenant_id=tenant_id, graph_id=graph_id, key=key)

    # ── Pipelines ──

    def tm_save_pipeline(
        self, tenant_id: str, graph_id: str, node_id: str,
        steps: list[dict[str, Any]] | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.save_pipeline(
            tenant_id=tenant_id, graph_id=graph_id, node_id=node_id, steps=steps or [],
        )

    def tm_get_pipeline(
        self, tenant_id: str, node_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any] | None:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.get_pipeline(tenant_id=tenant_id, node_id=node_id)

    # ── Layouts ──

    def tm_save_layout(
        self, tenant_id: str, graph_id: str,
        layout: dict[str, Any] | None = None, is_default: bool = False,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return {"error": "team_manager_disabled"}
        return runtime.team_manager.save_layout(
            tenant_id=tenant_id, graph_id=graph_id, layout=layout or {}, is_default=is_default,
        )

    def tm_list_layouts(
        self, tenant_id: str, graph_id: str, workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.team_manager is None:
            return []
        return runtime.team_manager.list_layouts(tenant_id=tenant_id, graph_id=graph_id)

    # ── AI Generation ──

    def tm_generate_text(
        self, tenant_id: str, prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        """Generate text using the configured LLM provider for Team Manager AI features."""
        provider = self.provider
        model = self.config.model_id or "anthropic/claude-haiku-4-5-20251001"
        # Use a fast model for generation tasks
        fast_model = model.replace("opus", "haiku").replace("sonnet", "haiku")
        if "haiku" not in fast_model:
            fast_model = "anthropic/claude-haiku-4-5-20251001"

        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        try:
            resp = provider.generate(fast_model, messages)
            return {"text": resp.text, "model": resp.model, "usage": resp.usage}
        except Exception as exc:
            return {"error": str(exc)}

    def get_user_profile(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.identity.get_profile(tenant_id, user_id)

    def list_pending_profile_signals(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.identity.list_pending_signals(tenant_id, user_id)

    def decide_profile_signal(
        self,
        tenant_id: str,
        user_id: str,
        signal_id: str,
        approved: bool,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.identity.decide_signal(tenant_id, user_id, signal_id, approved)

    def spawn_subagent(
        self,
        tenant_id: str,
        task: SubAgentTask,
        parent_session_id: str,
        parent_turn_id: str,
        parent_agent_id: str,
        child_agent_id: str,
        worker: SubAgentWorker,
        workspace_root: str | None = None,
        parent_run_id: str | None = None,
    ) -> SubAgentHandle:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.orchestrator.spawn_async(
            task=task,
            parent_session_id=parent_session_id,
            parent_turn_id=parent_turn_id,
            parent_agent_id=parent_agent_id,
            child_agent_id=child_agent_id,
            worker=worker,
            parent_run_id=parent_run_id,
        )

    def poll_subagent_events(
        self,
        tenant_id: str,
        run_id: str,
        after_seq: int = 0,
        workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        return runtime.protocol.stream_events(run_id=run_id, after_seq=after_seq)

    def approve_learning(
        self,
        tenant_id: str,
        user_id: str,
        update_id: str,
        approved: bool,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        decision = runtime.memory.approve_learning(update_id=update_id, approved=approved)
        return {
            "update_id": decision.update_id,
            "status": decision.status,
            "confidence": decision.confidence,
            "memory_id": decision.memory_id,
            "pending_approvals": runtime.memory.pending_approvals(tenant_id=tenant_id, user_id=user_id),
        }

    def list_artifacts(
        self,
        tenant_id: str,
        session_id: str,
        workspace_root: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        rows = runtime.artifacts.list_session_artifacts(tenant_id=tenant_id, session_id=session_id, limit=limit)
        return [self._artifact_dict(r) for r in rows]

    def start_autonomy(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        status: dict[str, Any] = {}
        if self.config.heartbeat_enabled:
            heartbeat = self._ensure_heartbeat_engine(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
            heartbeat.start()
            status["heartbeat"] = heartbeat.status()
        else:
            status["heartbeat"] = {"running": False, "reason": "disabled_by_config"}

        if self.config.cron_enabled:
            scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
            scheduler.start()
            status["cron"] = scheduler.status()
        else:
            status["cron"] = {"running": False, "reason": "disabled_by_config"}

        if self.config.dream_cycle_enabled:
            dc = self._ensure_dream_cycle()
            dc.start()
            status["dream_cycle"] = dc.status()
        else:
            status["dream_cycle"] = {"running": False, "reason": "disabled_by_config"}
        return status

    def heartbeat_status(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        heartbeat = self._ensure_heartbeat_engine(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return heartbeat.status()

    def heartbeat_start(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        heartbeat = self._ensure_heartbeat_engine(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        heartbeat.start()
        return heartbeat.status()

    def heartbeat_stop(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        key = self._autonomy_key(tenant_id, user_id, workspace_root)
        heartbeat = self._heartbeat_engines.get(key)
        if heartbeat is None:
            return {"running": False, "reason": "not_started"}
        heartbeat.stop()
        return heartbeat.status()

    def heartbeat_tick(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        heartbeat = self._ensure_heartbeat_engine(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return heartbeat.run_once()

    def cron_status(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.status()

    def cron_start(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        scheduler.start()
        return scheduler.status()

    def cron_stop(self, tenant_id: str, user_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        key = self._autonomy_key(tenant_id, user_id, workspace_root)
        scheduler = self._cron_schedulers.get(key)
        if scheduler is None:
            return {"running": False, "reason": "not_started"}
        scheduler.stop()
        return scheduler.status()

    def list_schedules(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str | None = None,
        include_disabled: bool = True,
    ) -> list[dict[str, Any]]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.list_tasks(include_disabled=include_disabled)

    def add_schedule(
        self,
        tenant_id: str,
        user_id: str,
        cron_expression: str,
        task_goal: str,
        workspace_root: str | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.add_task(cron_expression=cron_expression, task_goal=task_goal, enabled=enabled)

    def remove_schedule(
        self,
        tenant_id: str,
        user_id: str,
        task_id: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.remove_task(task_id=task_id)

    def set_schedule_enabled(
        self,
        tenant_id: str,
        user_id: str,
        task_id: str,
        enabled: bool,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.set_enabled(task_id=task_id, enabled=enabled)

    def run_due_schedules_once(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str | None = None,
    ) -> list[dict[str, Any]]:
        scheduler = self._ensure_cron_scheduler(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        return scheduler.run_due_once()

    # ------------------------------------------------------------------
    # Dream cycle
    # ------------------------------------------------------------------

    def dream_cycle_status(self) -> dict[str, Any]:
        dc = self._dream_cycle
        if dc is None:
            return {"running": False, "reason": "not_initialized"}
        return dc.status()

    def dream_cycle_start(self, dashboard_svc: Any = None) -> dict[str, Any]:
        dc = self._ensure_dream_cycle(dashboard_svc)
        dc.start()
        return dc.status()

    def dream_cycle_stop(self) -> dict[str, Any]:
        dc = self._dream_cycle
        if dc is None:
            return {"running": False}
        dc.stop()
        return dc.status()

    def dream_cycle_run_once(self, being_id: str | None = None, dashboard_svc: Any = None) -> dict[str, Any]:
        dc = self._ensure_dream_cycle(dashboard_svc)
        return dc.run_cycle(being_id=being_id)

    def _ensure_dream_cycle(self, dashboard_svc: Any = None) -> DreamCycle:
        if self._dream_cycle is not None:
            return self._dream_cycle
        self._dream_cycle = DreamCycle(
            bridge=self,
            dashboard_svc=dashboard_svc,
            interval_seconds=self.config.dream_cycle_interval_seconds,
        )
        return self._dream_cycle

    def list_sisters(self, tenant_id: str, workspace_root: str | None = None) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.sisters is None:
            return []
        return runtime.sisters.list_sisters()

    def sister_status(self, tenant_id: str, sister_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        sisters = self.list_sisters(tenant_id=tenant_id, workspace_root=workspace_root)
        for item in sisters:
            if str(item.get("sister_id")) == sister_id:
                return item
        raise ValueError(f"sister not found: {sister_id}")

    def spawn_sister(self, tenant_id: str, sister_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.sisters is None:
            raise ValueError("sister registry is not configured for this tenant")
        return runtime.sisters.spawn_sister(sister_id)

    def stop_sister(self, tenant_id: str, sister_id: str, workspace_root: str | None = None) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.sisters is None:
            raise ValueError("sister registry is not configured for this tenant")
        return runtime.sisters.stop_sister(sister_id)

    def message_sister(
        self,
        tenant_id: str,
        sister_id: str,
        message: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        if runtime.sisters is None:
            raise ValueError("sister registry is not configured for this tenant")
        sister = runtime.sisters.get_sister(sister_id)
        if sister is None:
            raise ValueError(f"sister not found: {sister_id}")
        result = self.handle_turn(
            TurnRequest(
                tenant_id=sister.tenant_id,
                session_id=f"sister-chat-{sister.sister_id}",
                user_id=f"prime->{sister.sister_id}",
                user_message=message,
                model_id=sister.model_id or None,
                profile=TurnProfile.TASK_EXECUTION,
                workspace_root=str(sister.workspace_root),
            )
        )
        return {
            "sister_id": sister_id,
            "session_id": result.get("turn", {}).get("session_id"),
            "turn_id": result.get("turn", {}).get("turn_id"),
            "response": result.get("assistant", {}).get("text", ""),
        }

    # ── Dashboard aggregation ────────────────────────────────────────

    def dashboard_overview(
        self, tenant_id: str, user_id: str, workspace_root: str | None = None,
    ) -> dict[str, Any]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        db = runtime.db
        now_iso = datetime.now(timezone.utc).isoformat()
        uptime_seconds = time.time() - self._start_time

        # ── runtime ──
        runtime_info = {
            "uptime_seconds": round(uptime_seconds, 1),
            "tenant_count": len(self._tenants),  # single dict read, GIL-safe
            "config": {
                "model_id": self.config.default_model_id,
                "provider": self.provider.provider_name,
                "agentic_loop": self.config.agentic_loop_enabled,
                "max_iterations": self.config.max_loop_iterations,
                "budget_limit_usd": self.config.budget_limit_usd,
                "tool_profile": self.config.tool_profile,
            },
            "active_threads": threading.active_count(),
        }

        # ── sessions ──
        try:
            row = db.execute(
                "SELECT COUNT(DISTINCT session_id) AS cnt FROM conversation_turns WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            session_count = row["cnt"] if row else 0
        except Exception:
            session_count = 0

        try:
            row = db.execute(
                "SELECT COUNT(*) AS cnt FROM conversation_turns WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            turn_count = row["cnt"] if row else 0
        except Exception:
            turn_count = 0

        try:
            row = db.execute(
                "SELECT AVG(iterations) AS avg_iter FROM loop_executions WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            avg_iterations = round(row["avg_iter"], 2) if row and row["avg_iter"] else 0
        except Exception:
            avg_iterations = 0

        sessions_info = {
            "total_sessions": session_count,
            "total_turns": turn_count,
            "avg_iterations": avg_iterations,
        }

        # ── tokens ──
        tokens_info = {"input_24h": 0, "output_24h": 0, "input_7d": 0, "output_7d": 0, "input_all": 0, "output_all": 0}
        try:
            for period, hours in [("24h", 24), ("7d", 168)]:
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                row = db.execute(
                    "SELECT COALESCE(SUM(total_input_tokens),0) AS inp, COALESCE(SUM(total_output_tokens),0) AS outp "
                    "FROM loop_executions WHERE tenant_id = ? AND created_at >= ?",
                    (tenant_id, cutoff),
                ).fetchone()
                if row:
                    tokens_info[f"input_{period}"] = row["inp"]
                    tokens_info[f"output_{period}"] = row["outp"]
            row = db.execute(
                "SELECT COALESCE(SUM(total_input_tokens),0) AS inp, COALESCE(SUM(total_output_tokens),0) AS outp "
                "FROM loop_executions WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if row:
                tokens_info["input_all"] = row["inp"]
                tokens_info["output_all"] = row["outp"]
        except Exception:
            pass

        # ── memory ──
        memory_info: dict[str, Any] = {}
        for table, key in [
            ("markdown_notes", "working_notes"),
            ("memories", "semantic_memories"),
            ("memory_archive", "archived_memories"),
            ("procedural_memories", "procedural_strategies"),
            ("conversation_turns", "conversation_turns"),
            ("session_summaries", "session_summaries"),
        ]:
            try:
                row = db.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
                memory_info[key] = row["cnt"] if row else 0
            except Exception:
                memory_info[key] = 0
        try:
            row = db.execute(
                "SELECT AVG(CAST(success_count AS REAL) / MAX(success_count + failure_count, 1)) AS avg_sr "
                "FROM procedural_memories"
            ).fetchone()
            memory_info["procedural_avg_success"] = round(row["avg_sr"], 3) if row and row["avg_sr"] else 0
        except Exception:
            memory_info["procedural_avg_success"] = 0

        # ── adaptation ──
        adaptation_info: dict[str, Any] = {}
        try:
            policy = runtime.adaptation.get_policy("default")
            adaptation_info["policy"] = policy if isinstance(policy, dict) else {"name": "default"}
        except Exception:
            adaptation_info["policy"] = {"name": "default"}
        try:
            rows = db.execute(
                "SELECT * FROM runtime_metrics_rollup ORDER BY rowid DESC LIMIT 2"
            ).fetchall()
            adaptation_info["recent_metrics"] = [dict(r) for r in rows]
        except Exception:
            adaptation_info["recent_metrics"] = []
        adaptation_info["turn_count"] = turn_count

        # ── sub-agents ──
        subagents_info: dict[str, Any] = {"active": 0, "completed": 0, "failed": 0, "runs": []}
        try:
            for status_val in ["running", "completed", "failed"]:
                row = db.execute(
                    "SELECT COUNT(*) AS cnt FROM subagent_runs WHERE tenant_id = ? AND status = ?",
                    (tenant_id, status_val),
                ).fetchone()
                key_name = status_val if status_val != "running" else "active"
                subagents_info[key_name] = row["cnt"] if row else 0
            rows = db.execute(
                "SELECT * FROM subagent_runs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 20",
                (tenant_id,),
            ).fetchall()
            subagents_info["runs"] = [dict(r) for r in rows]
        except Exception:
            pass

        # ── autonomy ──
        autonomy_info: dict[str, Any] = {}
        try:
            autonomy_info["heartbeat"] = self.heartbeat_status(tenant_id, user_id, workspace_root)
        except Exception:
            autonomy_info["heartbeat"] = {"running": False}
        try:
            autonomy_info["cron"] = self.cron_status(tenant_id, user_id, workspace_root)
        except Exception:
            autonomy_info["cron"] = {"running": False}
        try:
            autonomy_info["schedules"] = self.list_schedules(tenant_id, user_id, workspace_root)
        except Exception:
            autonomy_info["schedules"] = []
        autonomy_info["dream_cycle"] = self.dream_cycle_status()

        # ── skills ──
        try:
            skills_list = self.list_skills(tenant_id, workspace_root)
            skills_info = {
                "total": len(skills_list),
                "active": sum(1 for s in skills_list if s.get("status") == "active"),
            }
        except Exception:
            skills_info = {"total": 0, "active": 0}

        # ── governance ──
        try:
            approvals = self.list_pending_approvals(tenant_id, workspace_root)
            governance_info = {"pending_approvals": len(approvals)}
        except Exception:
            governance_info = {"pending_approvals": 0}

        # ── pinecone ──
        pinecone_info: dict[str, Any] = {
            "enabled": bool(self.config.pinecone_enabled),
            "connected": False,
            "index_count": 0,
            "total_vector_count": 0,
            "error": None,
        }
        if self.config.pinecone_enabled and "pinecone_list_indexes" in runtime.tool_executor.known_tool_names():
            try:
                policy = runtime.policy_pipeline.resolve(
                    ToolPolicyContext(
                        profile=self.config.tool_profile,
                        tenant_id=tenant_id,
                        provider_name=self.provider.provider_name,
                    ),
                    available_tools=runtime.tool_executor.known_tool_names(),
                )
                tool_ctx = ToolContext(
                    tenant_id=tenant_id,
                    session_id="dashboard",
                    turn_id=str(uuid.uuid4()),
                    user_id=user_id,
                    workspace_root=runtime.context.workspace_root,
                    db=runtime.db,
                    guard_path=lambda p: self.registry.guard_path(runtime.context, p),
                )
                result = runtime.tool_executor.execute(
                    tool_name="pinecone_list_indexes",
                    arguments={},
                    context=tool_ctx,
                    policy=policy,
                    confidence=1.0,
                )
                if result.status == "executed":
                    indexes = result.output.get("indexes")
                    if isinstance(indexes, list):
                        pinecone_info["connected"] = True
                        pinecone_info["index_count"] = len(indexes)
                        pinecone_info["total_vector_count"] = sum(
                            int(item.get("vector_count") or 0)
                            for item in indexes
                            if isinstance(item, dict)
                        )
                else:
                    pinecone_info["error"] = str(result.output.get("error") or result.output.get("reason") or result.status)
            except Exception as exc:
                pinecone_info["error"] = str(exc)

        # ── sisters ──
        try:
            sisters_info = {
                "total": 0,
                "running": 0,
                "items": [],
            }
            items = self.list_sisters(tenant_id=tenant_id, workspace_root=workspace_root)
            sisters_info["items"] = items
            sisters_info["total"] = len(items)
            sisters_info["running"] = sum(1 for item in items if bool(item.get("running")))
        except Exception:
            sisters_info = {"total": 0, "running": 0, "items": []}

        # ── loop telemetry ──
        loop_telemetry: list[dict[str, Any]] = []
        try:
            rows = db.execute(
                "SELECT * FROM loop_executions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 20",
                (tenant_id,),
            ).fetchall()
            loop_telemetry = [dict(r) for r in rows]
        except Exception:
            pass

        return {
            "timestamp": now_iso,
            "runtime": runtime_info,
            "sessions": sessions_info,
            "tokens": tokens_info,
            "memory": memory_info,
            "adaptation": adaptation_info,
            "subagents": subagents_info,
            "autonomy": autonomy_info,
            "skills": skills_info,
            "governance": governance_info,
            "pinecone": pinecone_info,
            "sisters": sisters_info,
            "loop_telemetry": loop_telemetry,
        }

    def dashboard_activity(
        self, tenant_id: str, user_id: str, workspace_root: str | None = None, limit: int = 50,
    ) -> list[dict[str, Any]]:
        runtime = self._tenant_runtime(tenant_id, workspace_root)
        db = runtime.db
        events: list[dict[str, Any]] = []

        try:
            rows = db.execute(
                "SELECT id, session_id, turn_id, iterations, stopped_reason, "
                "total_input_tokens, total_output_tokens, duration_ms, created_at "
                "FROM loop_executions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                events.append({
                    "type": "TURN",
                    "timestamp": rd.get("created_at", ""),
                    "session": rd.get("session_id", ""),
                    "description": f"Loop: {rd.get('iterations', 0)} iters, {rd.get('stopped_reason', 'unknown')}, "
                                   f"{rd.get('total_input_tokens', 0)}+{rd.get('total_output_tokens', 0)} tok",
                    "data": rd,
                })
        except Exception:
            pass

        try:
            rows = db.execute(
                "SELECT * FROM subagent_runs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                events.append({
                    "type": "SUBAGT",
                    "timestamp": rd.get("created_at", ""),
                    "session": rd.get("parent_session_id", ""),
                    "description": f"Sub-agent {rd.get('status', 'unknown')}: {rd.get('goal', '')[:80]}",
                    "data": rd,
                })
        except Exception:
            pass

        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return events[:limit]

    def _tenant_runtime(self, tenant_id: str, workspace_root: str | None = None) -> _TenantRuntime:
        key = tenant_id
        # Fast path: check without lock for existing tenants (dict reads are safe for single-key lookup)
        if key in self._tenants:
            existing = self._tenants[key]
            if workspace_root is not None:
                requested = os.path.realpath(os.path.abspath(os.path.expanduser(workspace_root)))
                bound = os.path.realpath(str(existing.context.workspace_root))
                if requested != bound:
                    raise ValueError(
                        f"tenant {tenant_id} already bound to workspace {bound}, requested {requested}"
                    )
            return existing

        # Slow path: acquire lock, double-check, then init
        with self._tenants_lock:
            # Double-check after acquiring lock
            if key in self._tenants:
                existing = self._tenants[key]
                if workspace_root is not None:
                    requested = os.path.realpath(os.path.abspath(os.path.expanduser(workspace_root)))
                    bound = os.path.realpath(str(existing.context.workspace_root))
                    if requested != bound:
                        raise ValueError(
                            f"tenant {tenant_id} already bound to workspace {bound}, requested {requested}"
                        )
                return existing

            context = self.registry.ensure_tenant(tenant_id=tenant_id, workspace_root=workspace_root)
            soul_config = load_soul_from_workspace(context.workspace_root)
            db = RuntimeDB(context.db_path)
            db.script(
                """
                CREATE TABLE IF NOT EXISTS loop_executions (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  turn_id TEXT NOT NULL,
                  iterations INTEGER NOT NULL,
                  tool_calls_json TEXT NOT NULL,
                  stopped_reason TEXT,
                  total_input_tokens INTEGER,
                  total_output_tokens INTEGER,
                  duration_ms INTEGER,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_loop_exec_tenant
                  ON loop_executions(tenant_id, created_at DESC);
                """
            )
            db.commit()

            if os.getenv("OPENROUTER_API_KEY"):
                capabilities = ModelCapabilityService(
                    db=db,
                    api_base=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    cache_ttl_seconds=self.config.capability_cache_ttl_seconds,
                )
            else:
                capabilities = ModelCapabilityService(
                    db=db,
                    fetcher=self._fallback_catalog,
                    cache_ttl_seconds=self.config.capability_cache_ttl_seconds,
                )

            protocol = SubAgentProtocol(db)
            from bomba_sr.subagents.worker import SubAgentWorkerFactory

            subagent_worker_factory = SubAgentWorkerFactory(self)
            default_subagent_worker = subagent_worker_factory.create_worker()
            orchestrator = SubAgentOrchestrator(
                protocol,
                crash_storm_config=CrashStormConfig(
                    window_seconds=self.config.subagent_crash_window_seconds,
                    max_crashes=self.config.subagent_crash_max,
                    cooldown_seconds=self.config.subagent_crash_cooldown_seconds,
                ),
                max_spawn_depth=self.config.subagent_max_spawn_depth,
                default_worker=default_subagent_worker,
            )
            codeintel = CodeIntelRouter(
                config=self.config,
                tenant_registry=self.registry,
                serena_transport=self.serena_transport,
            )

            governance = ToolGovernanceService(db)
            governance.upsert_default_policy(tenant_id)

            plugin_registry = PluginRegistry(
                allow=self.config.plugin_allow,
                deny=self.config.plugin_deny,
            )
            plugin_paths = [Path(p).expanduser() for p in self.config.plugin_paths]
            plugin_paths.append(context.workspace_root / ".bomba" / "plugins")
            plugin_paths.append(Path.home() / ".sigil" / "plugins")
            for manifest in plugin_registry.discover(plugin_paths):
                try:
                    plugin_registry.load(manifest)
                except Exception:
                    continue

            skills_registry = SkillRegistry(db)
            skills_engine = SkillEngine(skills_registry)
            skill_roots: list[Path]
            if self.config.skill_roots:
                skill_roots = [Path(p).expanduser() for p in self.config.skill_roots]
            else:
                skill_roots = [
                    *list_skill_roots(context.workspace_root),
                    Path.home() / ".sigil" / "skills",
                    Path("/opt/homebrew/lib/node_modules/openclaw/skills"),
                    Path(__file__).resolve().parents[1] / "skills" / "bundled",
                ]
            deduped_skill_roots: list[Path] = []
            seen_skill_roots: set[Path] = set()
            for root in skill_roots:
                resolved = root.expanduser().resolve()
                if resolved in seen_skill_roots:
                    continue
                seen_skill_roots.add(resolved)
                deduped_skill_roots.append(resolved)
            skill_roots = deduped_skill_roots
            plugin_skill_dirs = plugin_registry.get_skill_dirs()
            if plugin_skill_dirs:
                skill_roots = [skill_roots[0], *plugin_skill_dirs, *skill_roots[1:]]
            skill_parser = SkillMdParser(permissive=self.config.skill_parsing_permissive)
            skill_loader = SkillLoader(
                skill_roots=skill_roots,
                eligibility=EligibilityEngine(),
                parser=skill_parser,
            )
            for descriptor in skill_loader.scan().values():
                skills_registry.register_from_descriptor(
                    tenant_id=tenant_id,
                    descriptor=descriptor,
                    status=("active" if descriptor.default_enabled else "validated"),
                )
            if self.config.skill_watcher_enabled:
                skill_loader.start_watcher(self.config.skill_watcher_debounce_ms)

            search = AgenticSearchExecutor(context.workspace_root)
            memory = HybridMemoryStore(
                db=db,
                memory_root=context.memory_root,
                auto_apply_confidence=self.config.learning_auto_apply_confidence,
                embedding_provider=self.embedding_provider,
            )
            projects = ProjectService(db)
            team_manager = None
            if self.config.team_manager_enabled:
                from bomba_sr.runtime.team_manager import TeamManagerService
                team_manager = TeamManagerService(db)
            policy_pipeline = PolicyPipeline(
                governance=governance,
                global_allow=self.config.tool_allow,
                global_deny=self.config.tool_deny,
            )
            skills_ecosystem = SkillEcosystemService(
                db=db,
                registry=skills_registry,
                loader=skill_loader,
                parser=skill_parser,
                governance=governance,
                enabled_sources=self.config.skill_catalog_sources,
                telemetry_enabled=self.config.skills_telemetry_enabled,
                source_repos=self.config.skill_source_repo_overrides,
                clawhub_api_base=self.config.clawhub_api_base,
            )
            sisters_registry: SisterRegistry | None = None
            sisters_config_path = context.workspace_root / "sisters.json"
            if sisters_config_path.exists() or tenant_id in {"tenant-prime", "tenant-local", "prime"}:
                sisters_registry = SisterRegistry(
                    config_path=sisters_config_path,
                    orchestrator=orchestrator,
                    protocol=protocol,
                    parent_agent_id="prime",
                )
            tool_executor = ToolExecutor(
                governance=governance,
                pipeline=policy_pipeline,
                tool_result_max_chars=self.config.tool_result_max_chars,
            )
            tool_executor.register_many(builtin_fs_tools())
            tool_executor.register_many(
                builtin_exec_tools(default_max_output_chars=self.config.shell_output_max_chars)
            )
            tool_executor.register_many(builtin_search_tools(search=search, codeintel=codeintel, tenant_context=context))
            if self.config.web_search_enabled:
                tool_executor.register_many(builtin_web_tools(brave_api_key=self.config.brave_api_key))
                tool_executor.register_many(builtin_browser_tools())
            if self.config.pinecone_enabled:
                tool_executor.register_many(
                    builtin_pinecone_tools(
                        default_index=self.config.pinecone_default_index,
                        default_namespace=self.config.pinecone_default_namespace,
                    )
                )
            if self.config.supabase_enabled or self.config.postgres_enabled:
                tool_executor.register_many(
                    builtin_data_access_tools(
                        enable_supabase=self.config.supabase_enabled,
                        enable_postgres=self.config.postgres_enabled,
                    )
                )
            if self.config.voice_enabled:
                tool_executor.register_many(builtin_voice_tools(provider=self.config.voice_provider))
            if self.config.fal_enabled:
                tool_executor.register_many(builtin_fal_tools(default_video_model=self.config.fal_video_model))
            if self.config.colosseum_enabled:
                tool_executor.register_many(
                    builtin_colosseum_tools(
                        provider=self.provider,
                        default_model_id=self.config.colosseum_model_id,
                        workspace_root=context.workspace_root,
                    )
                )
            if self.config.prove_ahead_enabled:
                tool_executor.register_many(
                    builtin_prove_ahead_tools(
                        provider=self.provider,
                        default_model_id=self.config.default_model_id,
                        workspace_root=context.workspace_root,
                    )
                )
            if self.config.team_manager_enabled and team_manager is not None:
                from bomba_sr.tools.builtin_team import builtin_team_tools
                tool_executor.register_many(
                    builtin_team_tools(
                        team_manager=team_manager,
                        tenant_id=tenant_id,
                    )
                )
            tool_executor.register_many(builtin_memory_tools(memory))
            tool_executor.register_many(builtin_knowledge_tools())
            # Team context tool — only registered for Prime
            if "prime" in tenant_id.lower() or tenant_id == "tenant-local":
                tool_executor.register_many(builtin_team_context_tools())
            tool_executor.register_many(builtin_approval_tools(governance, memory))
            tool_executor.register_many(
                builtin_subagent_tools(
                    orchestrator=orchestrator,
                    protocol=protocol,
                    default_worker=default_subagent_worker,
                )
            )
            tool_executor.register_many(builtin_project_tools(projects))
            tool_executor.register_many(
                builtin_skill_tools(skill_loader, skills_registry, skills_ecosystem=skills_ecosystem)
            )
            tool_executor.register_many(
                builtin_scheduler_tools(
                    add_schedule=self.add_schedule,
                    list_schedules=self.list_schedules,
                    remove_schedule=self.remove_schedule,
                    set_schedule_enabled=self.set_schedule_enabled,
                )
            )
            tool_executor.register_many(
                builtin_compaction_tools(
                    provider=self.provider,
                    default_model_id=self.config.default_model_id,
                    compaction_model_id=os.getenv("BOMBA_COMPACTION_MODEL_ID"),
                )
            )
            tool_executor.register_many(builtin_model_switch_tools())
            tool_executor.register_many(builtin_discovery_tools())
            if sisters_registry is not None and sisters_registry.list_sisters():
                tool_executor.register_many(
                    builtin_sister_tools(
                        list_sisters=lambda: self.list_sisters(tenant_id, str(context.workspace_root)),
                        spawn_sister=lambda sister_id: self.spawn_sister(tenant_id, sister_id, str(context.workspace_root)),
                        stop_sister=lambda sister_id: self.stop_sister(tenant_id, sister_id, str(context.workspace_root)),
                        sister_status=lambda sister_id: self.sister_status(tenant_id, sister_id, str(context.workspace_root)),
                        message_sister=lambda sister_id, message: self.message_sister(
                            tenant_id,
                            sister_id,
                            message,
                            str(context.workspace_root),
                        ),
                    )
                )
            for plugin_tool in plugin_registry.get_tools():
                try:
                    tool_executor.register(plugin_tool)
                except Exception:
                    continue
            command_parser = CommandParser()
            command_router = CommandRouter(skill_loader=skill_loader, tool_executor=tool_executor)
            skill_disclosure = SkillDisclosure()

            runtime = _TenantRuntime(
                context=context,
                db=db,
                capabilities=capabilities,
                context_engine=ContextPolicyEngine(),
                search=search,
                memory=memory,
                protocol=protocol,
                orchestrator=orchestrator,
                adaptation=RuntimeAdaptationEngine(db),
                artifacts=ArtifactStore(db=db, artifacts_root=context.artifacts_root),
                codeintel=codeintel,
                governance=governance,
                projects=projects,
                skills_registry=skills_registry,
                skills_engine=skills_engine,
                skill_loader=skill_loader,
                skills_ecosystem=skills_ecosystem,
                plugin_registry=plugin_registry,
                policy_pipeline=policy_pipeline,
                tool_executor=tool_executor,
                command_parser=command_parser,
                command_router=command_router,
                skill_disclosure=skill_disclosure,
                identity=UserIdentityService(db, auto_apply_confidence=self.config.learning_auto_apply_confidence),
                soul=soul_config,
                sisters=sisters_registry,
                info=GenericInfoRetriever(enabled=self.config.generic_info_web_retrieval_enabled),
                team_manager=team_manager,
            )
            if sisters_registry is not None:
                for sister in sisters_registry.list_sisters():
                    if not bool(sister.get("auto_start")):
                        continue
                    if bool(sister.get("running")):
                        continue
                    try:
                        sisters_registry.spawn_sister(
                            str(sister["sister_id"]),
                            parent_session_id="sisters-autostart",
                        )
                    except Exception:
                        continue
            self._tenants[key] = runtime
            return runtime

    def _autonomy_key(self, tenant_id: str, user_id: str, workspace_root: str | None) -> str:
        runtime = self._tenant_runtime(tenant_id=tenant_id, workspace_root=workspace_root)
        return f"{tenant_id}:{user_id}:{runtime.context.workspace_root}"

    def _ensure_heartbeat_engine(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str | None = None,
    ) -> HeartbeatEngine:
        key = self._autonomy_key(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        existing = self._heartbeat_engines.get(key)
        if existing is not None:
            return existing
        runtime = self._tenant_runtime(tenant_id=tenant_id, workspace_root=workspace_root)

        def _runner(heartbeat_md: str) -> dict[str, Any]:
            return self._run_heartbeat_turn(
                tenant_id=tenant_id,
                user_id=user_id,
                workspace_root=str(runtime.context.workspace_root),
                heartbeat_md=heartbeat_md,
            )

        engine = HeartbeatEngine(
            tenant_id=tenant_id,
            user_id=user_id,
            workspace_root=runtime.context.workspace_root,
            runner=_runner,
            interval_seconds=self.config.heartbeat_interval_seconds,
        )
        self._heartbeat_engines[key] = engine
        return engine

    def _ensure_cron_scheduler(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str | None = None,
    ) -> CronScheduler:
        key = self._autonomy_key(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
        existing = self._cron_schedulers.get(key)
        if existing is not None:
            return existing
        runtime = self._tenant_runtime(tenant_id=tenant_id, workspace_root=workspace_root)

        def _runner(task_goal: str, task_id: str) -> dict[str, Any]:
            return self._run_scheduled_turn(
                tenant_id=tenant_id,
                user_id=user_id,
                workspace_root=str(runtime.context.workspace_root),
                task_goal=task_goal,
                task_id=task_id,
            )

        scheduler = CronScheduler(
            db=runtime.db,
            tenant_id=tenant_id,
            user_id=user_id,
            runner=_runner,
        )
        self._cron_schedulers[key] = scheduler
        return scheduler

    def _run_heartbeat_turn(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str,
        heartbeat_md: str,
    ) -> dict[str, Any]:
        result = self.handle_turn(
            TurnRequest(
                tenant_id=tenant_id,
                session_id=f"heartbeat-{uuid.uuid4()}",
                user_id=user_id,
                user_message=(
                    "[HEARTBEAT] Review the checklist below and act if needed. "
                    "Summarize any action taken.\n\n"
                    f"{heartbeat_md}"
                ),
                profile=TurnProfile.TASK_EXECUTION,
                workspace_root=workspace_root,
            )
        )
        return {
            "session_id": result.get("turn", {}).get("session_id"),
            "turn_id": result.get("turn", {}).get("turn_id"),
            "assistant_text": result.get("assistant", {}).get("text", ""),
        }

    def _run_scheduled_turn(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: str,
        task_goal: str,
        task_id: str,
    ) -> dict[str, Any]:
        result = self.handle_turn(
            TurnRequest(
                tenant_id=tenant_id,
                session_id=f"scheduled-{task_id}-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                user_message=f"scheduled task {task_id}: {task_goal}",
                profile=TurnProfile.TASK_EXECUTION,
                workspace_root=workspace_root,
            )
        )
        return {
            "session_id": result.get("turn", {}).get("session_id"),
            "turn_id": result.get("turn", {}).get("turn_id"),
            "assistant_text": result.get("assistant", {}).get("text", ""),
        }

    def _capabilities(self, runtime: _TenantRuntime, model_id: str):
        try:
            caps = runtime.capabilities.get_capabilities(model_id)
            return caps, "openrouter_live"
        except (CapabilityError, Exception):
            fallback = ModelCapabilityService(
                db=runtime.db,
                fetcher=self._fallback_catalog,
                cache_ttl_seconds=self.config.capability_cache_ttl_seconds,
            )
            return fallback.get_capabilities(model_id), "fallback_catalog"

    @staticmethod
    def _fallback_catalog() -> list[dict[str, Any]]:
        return [
            {
                "id": "anthropic/claude-opus-4.6",
                "context_length": 1_000_000,
                "supported_parameters": ["tools", "response_format"],
                "top_provider": {"context_length": 1_000_000, "max_completion_tokens": 128_000},
            },
            {
                "id": "openai/gpt-5.2-codex",
                "context_length": 400_000,
                "supported_parameters": ["tools", "response_format"],
                "top_provider": {"context_length": 400_000, "max_completion_tokens": 128_000},
            },
        ]

    @staticmethod
    def _semantic_candidates(recall: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in recall.get("semantic") or []:
            out.append(
                {
                    "text": item.get("content", ""),
                    "source": item.get("source", ""),
                    "recency_label": item.get("recency_ts", ""),
                    "contradictory": False,
                }
            )
        for item in recall.get("markdown") or []:
            out.append(
                {
                    "text": item.get("snippet", ""),
                    "source": item.get("source", ""),
                    "recency_label": item.get("created_at", ""),
                    "contradictory": False,
                }
            )
        return out

    @staticmethod
    def _policy_int(policy_values: dict[str, Any], key: str, default: int, min_value: int = 1) -> int:
        raw = policy_values.get(key, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(min_value, value)

    @staticmethod
    def _policy_float(policy_values: dict[str, Any], key: str, default: float, min_value: float = 0.0) -> float:
        raw = policy_values.get(key, default)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return default
        return max(min_value, value)

    @staticmethod
    def _policy_bool(policy_values: dict[str, Any], key: str, default: bool) -> bool:
        raw = policy_values.get(key, default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        if isinstance(raw, (int, float)):
            return bool(raw)
        return default

    def _record_conversation_turn(
        self,
        runtime: _TenantRuntime,
        request: TurnRequest,
        turn_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        try:
            runtime.memory.record_turn(
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                turn_id=turn_id,
                user_id=request.user_id,
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except Exception as exc:  # pragma: no cover - defensive persistence path
            logger.warning("failed to persist early-turn conversation record", exc_info=exc)

    @staticmethod
    def _cap_recent_turn_messages(
        recent_turn_messages: list[dict[str, Any]],
        replay_token_budget: int,
    ) -> list[ChatMessage]:
        if replay_token_budget <= 0 or not recent_turn_messages:
            return []

        selected_reversed: list[dict[str, Any]] = []
        used_tokens = 0
        for item in reversed(recent_turn_messages):
            role = str(item.get("role") or "").strip().lower()
            if role not in {"user", "assistant"}:
                continue
            content = item.get("content")
            if isinstance(content, str):
                token_cost = estimate_tokens(content)
            else:
                token_cost = estimate_tokens(json.dumps(content, ensure_ascii=True))
            if token_cost > replay_token_budget:
                continue
            if used_tokens + token_cost > replay_token_budget:
                continue
            selected_reversed.append({"role": role, "content": content})
            used_tokens += token_cost

        selected = list(reversed(selected_reversed))
        return [ChatMessage(role=item["role"], content=item["content"]) for item in selected]

    @staticmethod
    def _learning_signal(user_message: str) -> tuple[str, str, float, str] | None:
        cleaned = user_message.strip()
        if not cleaned:
            return None
        if cleaned.endswith("?"):
            return None

        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
        key = f"user_signal::{digest}"

        high_conf_patterns = [
            re.compile(r"\bmy name is\b", re.IGNORECASE),
            re.compile(r"\bi prefer\b", re.IGNORECASE),
            re.compile(r"\bi work on\b", re.IGNORECASE),
            re.compile(r"\bremember that\b", re.IGNORECASE),
            re.compile(r"\bcall me\b", re.IGNORECASE),
            re.compile(r"\bmy timezone is\b", re.IGNORECASE),
            re.compile(r"\bi use\b", re.IGNORECASE),
        ]
        for pattern in high_conf_patterns:
            if pattern.search(cleaned):
                return key, cleaned, 0.72, "explicit_user_profile_signal"

        return None

    @staticmethod
    def _extract_first_code_block(text: str) -> str | None:
        match = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", text, flags=re.DOTALL)
        if match is None:
            return None
        return match.group(1).strip()

    @staticmethod
    def _should_create_markdown_artifact(user_message: str) -> bool:
        text = user_message.strip().lower()
        if not text:
            return False

        # Avoid artifact spam for pure conversational turns.
        if text.endswith("?"):
            return False

        explicit_deliverable_patterns = [
            r"\bcreate\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bwrite\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bgenerate\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bdraft\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bsave\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bexport\b.*\b(markdown|doc|document|readme|report|summary|plan|spec)\b",
            r"\bartifact\b",
        ]
        return any(re.search(pattern, text) for pattern in explicit_deliverable_patterns)

    @staticmethod
    def _artifact_dict(a) -> dict[str, Any]:
        return {
            "artifact_id": a.artifact_id,
            "type": a.artifact_type,
            "title": a.title,
            "path": a.path,
            "preview": a.preview,
            "mime_type": a.mime_type,
            "project_id": a.project_id,
            "task_id": a.task_id,
            "created_at": a.created_at,
        }
