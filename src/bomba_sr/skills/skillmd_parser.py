from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from bomba_sr.skills.descriptor import SkillDescriptor, SkillEligibility, VALID_RISK_LEVELS


_FRONTMATTER_RE = re.compile(r"^\s*---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", re.DOTALL)


class SkillParseWarning(ValueError):
    pass


class SkillMdParser:
    def __init__(self, permissive: bool = False) -> None:
        self.permissive = permissive

    def parse_file(self, path: Path, include_body: bool = True) -> SkillDescriptor:
        content = path.read_text(encoding="utf-8")
        return self.parse_string(
            content=content,
            skill_id=path.parent.name,
            source_path=str(path.resolve()),
            include_body=include_body,
        )

    def parse_string(
        self,
        content: str,
        skill_id: str,
        source_path: str | None = None,
        include_body: bool = True,
    ) -> SkillDescriptor:
        frontmatter, body = self._extract_frontmatter(content)
        frontmatter, warnings = self._normalize_frontmatter(frontmatter, skill_id)
        metadata, metadata_warnings = self._parse_metadata(frontmatter)
        warnings.extend(metadata_warnings)
        eligibility = self._build_eligibility(metadata)

        intent_tags = self._string_tuple(frontmatter.get("intent_tags") or frontmatter.get("intent-tags"))
        tools_required = self._string_tuple(frontmatter.get("tools_required") or frontmatter.get("tools-required"))

        risk = str(frontmatter.get("risk_level") or frontmatter.get("risk-level") or "low").lower()
        if risk not in VALID_RISK_LEVELS:
            warnings.append(f"invalid risk level '{risk}' - defaulting to low")
            risk = "low"

        command_dispatch = frontmatter.get("command-dispatch")
        command_tool = frontmatter.get("command-tool")
        command_arg_mode = str(frontmatter.get("command-arg-mode") or "raw")
        allowed_tools = self._parse_allowed_tools(frontmatter.get("allowed-tools"))

        descriptor = SkillDescriptor(
            skill_id=skill_id,
            version=str(frontmatter.get("version") or "1.0.0"),
            name=str(frontmatter["name"]),
            description=str(frontmatter["description"]),
            source="filesystem",
            source_path=source_path,
            body_text=(body if include_body else ""),
            intent_tags=intent_tags,
            tools_required=tools_required,
            risk_level=risk,
            default_enabled=bool(frontmatter.get("default_enabled", frontmatter.get("default-enabled", True))),
            user_invocable=bool(frontmatter.get("user-invocable", True)),
            disable_model_invocation=bool(frontmatter.get("disable-model-invocation", False)),
            command_dispatch=(str(command_dispatch) if command_dispatch is not None else None),
            command_tool=(str(command_tool) if command_tool is not None else None),
            command_arg_mode=command_arg_mode,
            eligibility=eligibility,
            metadata=metadata,
            license=(str(frontmatter.get("license")) if frontmatter.get("license") is not None else None),
            compatibility=(str(frontmatter.get("compatibility")) if frontmatter.get("compatibility") is not None else None),
            allowed_tools=allowed_tools,
            _body_loaded=include_body,
        )
        if warnings:
            descriptor.metadata.setdefault("sigil_warnings", warnings)
        return descriptor

    @staticmethod
    def _extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        match = _FRONTMATTER_RE.match(content)
        if match is None:
            raise ValueError("invalid SKILL.md: missing YAML frontmatter delimiters")
        raw_frontmatter = match.group(1)
        body = match.group(2).strip()
        parsed = yaml.safe_load(raw_frontmatter)
        if not isinstance(parsed, dict):
            raise ValueError("invalid SKILL.md: frontmatter must be an object")
        return parsed, body

    def parse_file_with_diagnostics(
        self,
        path: Path,
        include_body: bool = True,
        permissive: bool | None = None,
    ) -> tuple[SkillDescriptor | None, list[str]]:
        raw = path.read_text(encoding="utf-8")
        skill_id = path.parent.name
        mode = self.permissive if permissive is None else permissive
        if not mode:
            descriptor = self.parse_string(raw, skill_id=skill_id, source_path=str(path.resolve()), include_body=include_body)
            warnings = descriptor.metadata.get("sigil_warnings", [])
            return descriptor, [str(w) for w in warnings] if isinstance(warnings, list) else []
        try:
            descriptor = self.parse_string(raw, skill_id=skill_id, source_path=str(path.resolve()), include_body=include_body)
            warnings = descriptor.metadata.get("sigil_warnings", [])
            return descriptor, [str(w) for w in warnings] if isinstance(warnings, list) else []
        except Exception as exc:
            fallback = SkillDescriptor(
                skill_id=skill_id,
                version="1.0.0",
                name=skill_id,
                description=f"Imported skill {skill_id} (permissive parse fallback)",
                source="filesystem",
                source_path=str(path.resolve()),
                body_text=raw.strip() if include_body else "",
                intent_tags=(),
                tools_required=(),
                risk_level="low",
                default_enabled=True,
                user_invocable=True,
                disable_model_invocation=False,
                command_dispatch=None,
                command_tool=None,
                command_arg_mode="raw",
                eligibility=SkillEligibility(),
                metadata={"sigil_warnings": [f"fallback parse: {exc}"]},
                license=None,
                compatibility=None,
                allowed_tools=(),
                _body_loaded=include_body,
            )
            return fallback, [f"fallback parse: {exc}"]

    def _normalize_frontmatter(self, frontmatter: dict[str, Any], skill_id: str) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        out = dict(frontmatter)
        name = out.get("name")
        if not isinstance(name, str) or not name.strip():
            if self.permissive:
                warnings.append("missing 'name' - defaulted to skill_id")
                out["name"] = skill_id
            else:
                raise ValueError("invalid SKILL.md: frontmatter field 'name' is required")
        description = out.get("description")
        if not isinstance(description, str) or not description.strip():
            if self.permissive:
                warnings.append("missing 'description' - defaulted to placeholder")
                out["description"] = f"Skill {skill_id}"
            else:
                raise ValueError("invalid SKILL.md: frontmatter field 'description' is required")
        return out, warnings

    def _parse_metadata(self, frontmatter: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        raw = frontmatter.get("metadata")
        if raw is None:
            return {}, warnings
        if isinstance(raw, dict):
            return dict(raw), warnings
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                if self.permissive:
                    warnings.append(f"invalid metadata JSON ignored: {exc}")
                    return {}, warnings
                raise ValueError(f"invalid SKILL.md metadata: {exc}") from exc
            if not isinstance(parsed, dict):
                if self.permissive:
                    warnings.append("invalid metadata JSON type ignored (expected object)")
                    return {}, warnings
                raise ValueError("invalid SKILL.md metadata: expected object JSON")
            return parsed, warnings
        if self.permissive:
            warnings.append("invalid metadata type ignored")
            return {}, warnings
        raise ValueError("invalid SKILL.md metadata: expected object or JSON string")

    @staticmethod
    def _build_eligibility(metadata: dict[str, Any]) -> SkillEligibility:
        sigil = metadata.get("sigil") if isinstance(metadata.get("sigil"), dict) else {}
        openclaw = metadata.get("openclaw") if isinstance(metadata.get("openclaw"), dict) else {}
        selected = sigil if sigil else openclaw

        requires = selected.get("requires") if isinstance(selected.get("requires"), dict) else {}
        os_filter = selected.get("os") if isinstance(selected.get("os"), list) else []
        required_bins = requires.get("bins") if isinstance(requires.get("bins"), list) else []
        any_bins = requires.get("anyBins") if isinstance(requires.get("anyBins"), list) else []
        required_env = requires.get("env") if isinstance(requires.get("env"), list) else []
        required_config = requires.get("config") if isinstance(requires.get("config"), list) else []

        return SkillEligibility(
            always=bool(selected.get("always", False)),
            os_filter=tuple(str(x) for x in os_filter if str(x).strip()),
            required_bins=tuple(str(x) for x in required_bins if str(x).strip()),
            any_bins=tuple(str(x) for x in any_bins if str(x).strip()),
            required_env=tuple(str(x) for x in required_env if str(x).strip()),
            required_config=tuple(str(x) for x in required_config if str(x).strip()),
        )

    @staticmethod
    def _string_tuple(raw: Any) -> tuple[str, ...]:
        if not isinstance(raw, list):
            return ()
        return tuple(str(x) for x in raw if str(x).strip())

    @staticmethod
    def _parse_allowed_tools(raw: Any) -> tuple[str, ...]:
        if isinstance(raw, list):
            return tuple(str(x) for x in raw if str(x).strip())
        if isinstance(raw, str):
            return tuple(part for part in (x.strip() for x in raw.split()) if part)
        return ()
