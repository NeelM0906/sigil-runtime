from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.governance.tool_profiles import PROFILE_TOOLS, ToolProfile, profile_from_value, resolve_alias


@dataclass(frozen=True)
class ResolvedPolicy:
    allowed_tools: frozenset[str] | None
    denied_tools: frozenset[str]
    profile: ToolProfile
    source_layers: tuple[str, ...]


@dataclass(frozen=True)
class ToolPolicyContext:
    profile: ToolProfile
    tenant_id: str
    provider_name: str | None = None
    agent_id: str | None = None


class PolicyPipeline:
    def __init__(
        self,
        governance: ToolGovernanceService,
        global_allow: Iterable[str] = (),
        global_deny: Iterable[str] = (),
    ) -> None:
        self.governance = governance
        self.global_allow = frozenset(resolve_alias(x) for x in global_allow if str(x).strip())
        self.global_deny = frozenset(resolve_alias(x) for x in global_deny if str(x).strip())

    def resolve(
        self,
        context: ToolPolicyContext,
        available_tools: Iterable[str] | None = None,
    ) -> ResolvedPolicy:
        layers: list[str] = []
        available = None
        if available_tools is not None:
            available = {resolve_alias(x) for x in available_tools}

        profile = profile_from_value(context.profile)
        base_allowed = PROFILE_TOOLS[profile]
        if base_allowed is None:
            allowed: set[str] | None = None
        else:
            allowed = set(resolve_alias(x) for x in base_allowed)
            if available is not None:
                allowed &= available
        layers.append(f"profile:{profile.value}")

        tenant_allow, tenant_deny = self._tenant_overrides(context.tenant_id)
        if tenant_allow:
            layers.append("tenant_allow")
            if allowed is None:
                allowed = set(tenant_allow)
            else:
                allowed &= set(tenant_allow)
        if tenant_deny:
            layers.append("tenant_deny")

        if self.global_allow:
            layers.append("global_allow")
            if allowed is None:
                allowed = set(self.global_allow)
            else:
                allowed &= set(self.global_allow)

        denied = set(resolve_alias(x) for x in tenant_deny) | set(self.global_deny)
        if denied:
            layers.append("deny")

        if available is not None and allowed is None:
            allowed = set(available)

        if allowed is not None:
            allowed -= denied

        return ResolvedPolicy(
            allowed_tools=(frozenset(allowed) if allowed is not None else None),
            denied_tools=frozenset(denied),
            profile=profile,
            source_layers=tuple(layers),
        )

    @staticmethod
    def is_tool_allowed(tool_name: str, resolved: ResolvedPolicy) -> bool:
        canonical = resolve_alias(tool_name)
        if canonical in resolved.denied_tools:
            return False
        if resolved.allowed_tools is None:
            return True
        return canonical in resolved.allowed_tools

    def _tenant_overrides(self, tenant_id: str) -> tuple[frozenset[str], frozenset[str]]:
        row = self.governance.db.execute(
            """
            SELECT policy_json FROM tool_governance_policies
            WHERE tenant_id = ? AND policy_name = 'default'
            ORDER BY version DESC LIMIT 1
            """,
            (tenant_id,),
        ).fetchone()
        if row is None:
            return frozenset(), frozenset()
        try:
            payload = json.loads(str(row["policy_json"]))
        except json.JSONDecodeError:
            return frozenset(), frozenset()

        allow = payload.get("allow") if isinstance(payload.get("allow"), list) else []
        deny = payload.get("deny") if isinstance(payload.get("deny"), list) else []
        resolved_allow = frozenset(resolve_alias(str(x)) for x in allow if str(x).strip())
        resolved_deny = frozenset(resolve_alias(str(x)) for x in deny if str(x).strip())
        return resolved_allow, resolved_deny
