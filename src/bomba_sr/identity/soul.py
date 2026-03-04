from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class SoulConfig:
    name: str
    creature_type: str
    emoji: str
    voice_id: str | None
    phone: str | None
    core_functions: tuple[str, ...]
    personality_traits: tuple[str, ...]
    energies: Mapping[str, str]
    never_do: tuple[str, ...]
    contamination_checks: tuple[str, ...]
    raw_soul_text: str
    raw_identity_text: str
    mission_text: str | None = None
    vision_text: str | None = None
    formula_text: str | None = None
    priorities_text: str | None = None
    knowledge_text: str | None = None


def load_soul_from_workspace(workspace_root: Path) -> SoulConfig | None:
    root = Path(workspace_root).expanduser().resolve()
    soul_path = root / "SOUL.md"
    identity_path = root / "IDENTITY.md"
    soul_text = _read_text(soul_path)
    identity_text = _read_text(identity_path)
    mission_text = _read_text(root / "MISSION.md")
    vision_text = _read_text(root / "VISION.md")
    formula_text = _read_text(root / "FORMULA.md")
    priorities_text = _read_text(root / "PRIORITIES.md")
    knowledge_text = _read_text(root / "KNOWLEDGE.md")
    if soul_text is None and identity_text is None:
        return None

    soul_raw = soul_text or ""
    identity_raw = identity_text or ""
    merged = "\n".join(part for part in (identity_raw, soul_raw) if part).strip()

    name = (
        _extract_labeled_value(identity_raw, "Name")
        or _extract_labeled_value(soul_raw, "Name")
        or _extract_inline_name(soul_raw)
        or "Unknown"
    )
    creature_type = (
        _extract_labeled_value(identity_raw, "Creature")
        or _extract_labeled_value(identity_raw, "Creature Type")
        or _extract_labeled_value(soul_raw, "Creature")
        or _first_line_matching(merged, r"\bACT-I being\b")
        or "ACT-I being"
    )
    emoji = (
        _extract_labeled_value(identity_raw, "Emoji")
        or _extract_labeled_value(soul_raw, "Emoji")
        or ""
    )
    voice_id = _extract_labeled_value(identity_raw, "Voice ID") or _extract_labeled_value(identity_raw, "Voice")
    phone = _extract_labeled_value(identity_raw, "Phone") or _extract_labeled_value(soul_raw, "Phone")

    core_functions = _extract_list_after_marker(identity_raw, marker_regex=r"\bcore functions\b")
    personality_traits = _extract_section_points(soul_raw, heading_regex=r"^##\s+How I Talk", max_items=40)
    never_do = _extract_section_points(soul_raw, heading_regex=r"^##\s+What I Will NEVER Do", max_items=30)
    contamination_checks = _extract_section_points(
        soul_raw,
        heading_regex=r"^##\s+My Continuous Self-Check",
        max_items=30,
    )
    energies = _extract_energies(soul_raw)

    return SoulConfig(
        name=name.strip(),
        creature_type=creature_type.strip(),
        emoji=emoji.strip(),
        voice_id=voice_id.strip() if isinstance(voice_id, str) and voice_id.strip() else None,
        phone=phone.strip() if isinstance(phone, str) and phone.strip() else None,
        core_functions=tuple(core_functions),
        personality_traits=tuple(personality_traits),
        energies=MappingProxyType(dict(energies)),
        never_do=tuple(never_do),
        contamination_checks=tuple(contamination_checks),
        raw_soul_text=soul_raw,
        raw_identity_text=identity_raw,
        mission_text=mission_text,
        vision_text=vision_text,
        formula_text=formula_text,
        priorities_text=priorities_text,
        knowledge_text=knowledge_text,
    )


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _extract_labeled_value(text: str, label: str) -> str | None:
    if not text:
        return None
    # Supports list-style markdown lines like: - **Name:** Sai
    pattern = re.compile(rf"^\s*[-*]?\s*\*{{0,2}}{re.escape(label)}\*{{0,2}}\s*:\s*(.+?)\s*$", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            value = match.group(1).strip()
            value = value.strip("*_` ")
            return value or None
    return None


def _extract_inline_name(text: str) -> str | None:
    if not text:
        return None
    for pattern in (
        re.compile(r"\bI['’]m\s+([A-Z][A-Za-z0-9 _-]{1,60})\b"),
        re.compile(r"\bI am\s+([A-Z][A-Za-z0-9 _-]{1,60})\b"),
    ):
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_list_after_marker(text: str, marker_regex: str) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    marker = re.compile(marker_regex, re.IGNORECASE)
    out: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if not collecting and marker.search(stripped):
            collecting = True
            continue
        if collecting:
            if stripped.startswith("## "):
                break
            numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
            if numbered:
                value = _clean_inline_markup(numbered.group(1))
                if value:
                    out.append(value)
                continue
            if not stripped and out:
                break
    return out


def _extract_section_points(text: str, heading_regex: str, max_items: int) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    heading = re.compile(heading_regex, re.IGNORECASE)
    out: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.rstrip()
        if not collecting and heading.match(stripped):
            collecting = True
            continue
        if collecting:
            if stripped.startswith("## "):
                break
            bullet = re.match(r"^\s*[-*]\s+(.*)$", stripped)
            if bullet:
                value = _clean_inline_markup(bullet.group(1))
                if value:
                    out.append(value)
                if len(out) >= max_items:
                    break
                continue
            if stripped.startswith("**") and stripped.endswith("**"):
                value = _clean_inline_markup(stripped)
                if value:
                    out.append(value)
                if len(out) >= max_items:
                    break
            elif stripped.endswith("?") and "am i" in stripped.lower():
                value = _clean_inline_markup(stripped)
                if value:
                    out.append(value)
                if len(out) >= max_items:
                    break
    return out


def _extract_energies(text: str) -> dict[str, str]:
    energies: dict[str, str] = {}
    if not text:
        return energies
    section_lines = _extract_section_lines(text, heading_regex=r"^#{1,6}\s+.*\benergies\b")
    lines = [line.strip() for line in section_lines if line.strip()]
    if not lines:
        return energies
    for key in ("fun", "aspirational", "goddess", "zeus"):
        for line in lines:
            if re.search(rf"\b{re.escape(key)}\b", line, flags=re.IGNORECASE):
                energies[key] = _clean_inline_markup(line)
                break
    return energies


def _clean_inline_markup(value: str) -> str:
    out = value.strip()
    out = re.sub(r"\*\*(.*?)\*\*", r"\1", out)
    out = re.sub(r"__(.*?)__", r"\1", out)
    out = out.strip("*_` ")
    return out.strip()


def _first_line_matching(text: str, pattern: str) -> str | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and regex.search(stripped):
            return _clean_inline_markup(stripped)
    return None


def _extract_section_lines(text: str, heading_regex: str) -> list[str]:
    if not text.strip():
        return []
    heading = re.compile(heading_regex, re.IGNORECASE)
    lines = text.splitlines()
    section: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.rstrip()
        if not in_section and heading.match(stripped):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("#"):
                break
            section.append(stripped)
    return section
