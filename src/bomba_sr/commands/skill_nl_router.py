from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


IntentName = Literal[
    "catalog_list",
    "trust_get",
    "trust_set",
    "install_request",
    "install_apply",
    "install_requests_list",
    "diagnostics",
    "telemetry",
]


SOURCE_ALIASES = {
    "clawhub": "clawhub",
    "openclaw": "clawhub",
    "open claw": "clawhub",
    "anthropic": "anthropic_skills",
    "anthropic skills": "anthropic_skills",
    "anthropics": "anthropic_skills",
}

TRUST_ALIASES = {
    "read only": "read_only",
    "readonly": "read_only",
    "read_only": "read_only",
    "approval": "allow_with_approval",
    "allow with approval": "allow_with_approval",
    "allow_with_approval": "allow_with_approval",
    "blocked": "blocked",
    "block": "blocked",
}


@dataclass(frozen=True)
class SkillNlIntent:
    name: IntentName
    source: str | None = None
    skill_id: str | None = None
    trust_mode: str | None = None
    request_id: str | None = None
    limit: int | None = None


def parse_skill_nl_intent(text: str) -> SkillNlIntent | None:
    raw = text.strip()
    lowered = raw.lower()

    if "skill telemetry" in lowered or "skills telemetry" in lowered:
        return SkillNlIntent(name="telemetry", limit=_extract_limit(lowered))
    if "skill warning" in lowered or "skills warning" in lowered or "skills diagnostics" in lowered:
        return SkillNlIntent(name="diagnostics")

    if any(k in lowered for k in ["install requests", "installation requests", "skill install requests"]):
        return SkillNlIntent(name="install_requests_list")

    if _contains_any(lowered, ["apply install request", "install request", "execute install request"]):
        req_id = _extract_request_id(raw)
        if req_id:
            return SkillNlIntent(name="install_apply", request_id=req_id)
        return None

    if _contains_any(lowered, ["set trust", "change trust", "trust source", "trust mode"]):
        source = _extract_source(lowered)
        trust_mode = _extract_trust_mode(lowered)
        if source and trust_mode:
            return SkillNlIntent(name="trust_set", source=source, trust_mode=trust_mode)
        return None

    if _contains_any(lowered, ["show trust", "what is trust", "trust settings", "trust policy"]):
        return SkillNlIntent(name="trust_get")

    if _contains_any(lowered, ["catalog", "list skills from", "show skills from", "find skills from"]):
        source = _extract_source(lowered)
        return SkillNlIntent(name="catalog_list", source=source, limit=_extract_limit(lowered))

    # Mutating install request requires explicit install verbs.
    if _contains_any(lowered, ["install skill", "add skill", "install ", "add the skill"]):
        source = _extract_source(lowered)
        skill_id = _extract_skill_id(raw)
        if source and skill_id:
            return SkillNlIntent(name="install_request", source=source, skill_id=skill_id)
        return None

    return None


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(n in text for n in needles)


def _extract_source(text: str) -> str | None:
    for key, value in SOURCE_ALIASES.items():
        if key in text:
            return value
    return None


def _extract_trust_mode(text: str) -> str | None:
    for key, value in TRUST_ALIASES.items():
        if key in text:
            return value
    return None


def _extract_limit(text: str) -> int | None:
    match = re.search(r"\b(\d{1,4})\b", text)
    if not match:
        return None
    value = int(match.group(1))
    return max(1, min(500, value))


def _extract_request_id(text: str) -> str | None:
    # UUID request ids.
    match = re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        text,
    )
    return match.group(0) if match else None


def _extract_skill_id(text: str) -> str | None:
    # Prefer quoted ids in natural language.
    quoted = re.findall(r"['\"]([a-zA-Z0-9_-]{2,100})['\"]", text)
    if quoted:
        return quoted[0].strip().lower()

    lowered = text.lower()
    # Patterns like: install skill daily-brief from clawhub
    match = re.search(r"(?:install|add)\s+(?:the\s+)?(?:skill\s+)?([a-zA-Z0-9_-]{2,100})\s+from\s+", lowered)
    if match:
        return match.group(1).strip().lower()
    return None
