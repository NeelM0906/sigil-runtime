from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal


VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class SkillEligibility:
    always: bool = False
    os_filter: tuple[str, ...] = ()
    required_bins: tuple[str, ...] = ()
    any_bins: tuple[str, ...] = ()
    required_env: tuple[str, ...] = ()
    required_config: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillDescriptor:
    skill_id: str
    version: str
    name: str
    description: str
    source: Literal["filesystem", "database"]
    source_path: str | None
    body_text: str
    intent_tags: tuple[str, ...]
    tools_required: tuple[str, ...]
    risk_level: str
    default_enabled: bool
    user_invocable: bool
    disable_model_invocation: bool
    command_dispatch: str | None
    command_tool: str | None
    command_arg_mode: str
    eligibility: SkillEligibility
    metadata: dict[str, Any]
    license: str | None = None
    compatibility: str | None = None
    allowed_tools: tuple[str, ...] = ()
    _body_loaded: bool = False

    def with_body(self, body_text: str) -> "SkillDescriptor":
        return replace(self, body_text=body_text, _body_loaded=True)


def descriptor_from_manifest(
    manifest: dict[str, Any],
    *,
    source: Literal["filesystem", "database"] = "database",
    source_path: str | None = None,
) -> SkillDescriptor:
    risk = str(manifest.get("risk_level") or "low").lower()
    if risk not in VALID_RISK_LEVELS:
        risk = "low"

    raw_tags = manifest.get("intent_tags") or []
    if not isinstance(raw_tags, list):
        raw_tags = []

    raw_tools = manifest.get("tools_required") or []
    if not isinstance(raw_tools, list):
        raw_tools = []

    return SkillDescriptor(
        skill_id=str(manifest.get("skill_id") or ""),
        version=str(manifest.get("version") or "1.0.0"),
        name=str(manifest.get("name") or ""),
        description=str(manifest.get("description") or ""),
        source=source,
        source_path=source_path,
        body_text="",
        intent_tags=tuple(str(x) for x in raw_tags if str(x).strip()),
        tools_required=tuple(str(x) for x in raw_tools if str(x).strip()),
        risk_level=risk,
        default_enabled=bool(manifest.get("default_enabled", True)),
        user_invocable=bool(manifest.get("user_invocable", True)),
        disable_model_invocation=bool(manifest.get("disable_model_invocation", False)),
        command_dispatch=None,
        command_tool=None,
        command_arg_mode="raw",
        eligibility=SkillEligibility(),
        metadata={},
        license=(str(manifest.get("license")) if manifest.get("license") is not None else None),
        compatibility=(str(manifest.get("compatibility")) if manifest.get("compatibility") is not None else None),
        allowed_tools=tuple(
            str(x)
            for x in (manifest.get("allowed_tools") or [])
            if str(x).strip()
        ),
        _body_loaded=False,
    )
