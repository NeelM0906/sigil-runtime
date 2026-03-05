"""ACT-I Architecture Loader.

Parses the ACT-I being/cluster/lever/skill-family definitions from the
``workspaces/acti-architecture/`` directory and exposes them as plain dicts
for use by the dashboard and orchestration engine.

All data is **read-only** — this module never writes to the architecture files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ACTI_ROOT = _PROJECT_ROOT / "workspaces" / "acti-architecture"

# ── Being → Sister mapping (authoritative) ──────────────────────────────
BEING_SISTER_MAP: dict[str, str] = {
    "sai-prime": "prime",
    "executive-assistant": "prime",
    "the-strategist": "prime",
    "the-operator": "prime",
    "the-analyst": "scholar",
    "the-researcher": "scholar",
    "the-writer": "forge",
    "the-visual-architect": "forge",
    "the-filmmaker": "forge",
    "the-sound-engineer": "forge",
    "the-stage-director": "forge",
    "the-voice": "forge",
    "the-media-buyer": "forge",
    "the-messenger": "forge",
    "the-technologist": "forge",
    "the-connector": "recovery",
    "the-agreement-maker": "recovery",
    "the-keeper": "recovery",
    "the-multiplier": "recovery",
}

# ── Lever definitions ────────────────────────────────────────────────────
LEVERS: list[dict[str, str]] = [
    {"id": "0.5", "name": "Shared Experiences / First Touch"},
    {"id": "1", "name": "Ecosystem Mergers / Partnerships"},
    {"id": "2", "name": "Speaking / Content & Influence"},
    {"id": "3", "name": "Revenue / Agreements"},
    {"id": "4", "name": "Operations / Execution"},
    {"id": "5", "name": "Analytics / Intelligence"},
    {"id": "6", "name": "Community / Impact"},
    {"id": "7", "name": "Production / Infrastructure"},
]

LEVER_IDS = [lv["id"] for lv in LEVERS]

# ── Shared Heart Skills ──────────────────────────────────────────────────
SHARED_HEART_SKILLS: list[dict[str, str]] = [
    {
        "id": "level-5-listening",
        "name": "Level 5 Listening",
        "description": (
            "Highest tier of active listening — fully present, non-judgmental, "
            "listening to understand rather than respond."
        ),
    },
    {
        "id": "speaking-into-truth",
        "name": "Speaking Into Truth",
        "description": (
            "Direct, honest, purposeful communication with integrity and clarity."
        ),
    },
    {
        "id": "ghic",
        "name": "GHIC",
        "description": (
            "ACT-I proprietary communication and intelligence framework."
        ),
    },
    {
        "id": "4-step-communication",
        "name": "4-Step Communication Model (4-1-2-4)",
        "description": (
            "Structured communication protocol for consistency, clarity, "
            "and impact across all formats."
        ),
    },
]

# ── Regex helpers ────────────────────────────────────────────────────────
_POSITIONS_RE = re.compile(r"\*\*Positions:\*\*\s*(\d[\d,]*)")
_LEVERS_RE = re.compile(r"\*\*Levers:\*\*\s*([\d.,\s]+)")
_ID_RE = re.compile(r"\*\*ID:\*\*\s*#?(\w+)")
_TYPE_RE = re.compile(r"\*\*Type:\*\*\s*(.+)")
_DOMAIN_RE = re.compile(r"## Domain\n(.+?)(?:\n#|\Z)", re.DOTALL)
_CLUSTER_LINE_RE = re.compile(
    r"^- (\w[\w\s-]*?)\s*—\s*(.+?)\s*\((\d+)p\)\s*\[Family:\s*(.+?)\]",
    re.MULTILINE,
)

# Cluster file header parsing
_CLUSTER_FAMILY_RE = re.compile(r"\*\*Family:\*\*\s*(.+?)\s*\|")
_CLUSTER_BEING_RE = re.compile(r"\*\*Being:\*\*\s*(.+?)\s*\|")
_CLUSTER_TIER_RE = re.compile(r"\*\*Tier:\*\*\s*(.+?)\s*\|")
_CLUSTER_POS_RE = re.compile(r"\*\*Positions:\*\*\s*(\d+)")
_CLUSTER_FUNC_RE = re.compile(r"## Function\n(.+?)(?:\n#|\Z)", re.DOTALL)
_CLUSTER_DESC_RE = re.compile(r"## Description\n(.+?)(?:\n#|\Z)", re.DOTALL)

# Skill family table parsing
_FAMILY_ROW_RE = re.compile(
    r"\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|\s*(.+?)\s*\|"
)


# ── Singleton cache ──────────────────────────────────────────────────────
_cache: dict[str, Any] = {}


def _invalidate_cache() -> None:
    """Clear the in-memory cache (mainly for tests)."""
    _cache.clear()


# ── Public loaders ───────────────────────────────────────────────────────

def load_beings(root: Path | None = None) -> list[dict[str, Any]]:
    """Load all 19 ACT-I being definitions.

    Returns a list of dicts with keys:
        id, name, acti_id, type, positions, domain, levers, clusters,
        sister_id, shared_heart_skills
    """
    if "beings" in _cache:
        return _cache["beings"]

    root = root or _ACTI_ROOT
    beings_dir = root / "beings"
    if not beings_dir.is_dir():
        return []

    beings: list[dict[str, Any]] = []
    for md_file in sorted(beings_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        slug = md_file.stem  # e.g. "the-analyst"

        name = text.split("\n", 1)[0].lstrip("# ").strip()

        acti_id_m = _ID_RE.search(text)
        acti_id = acti_id_m.group(1) if acti_id_m else ""

        type_m = _TYPE_RE.search(text)
        being_type = type_m.group(1).strip() if type_m else ""

        pos_m = _POSITIONS_RE.search(text)
        positions = int(pos_m.group(1).replace(",", "")) if pos_m else 0

        levers_m = _LEVERS_RE.search(text)
        levers: list[str] = []
        if levers_m:
            levers = [lv.strip() for lv in levers_m.group(1).split(",") if lv.strip()]

        domain_m = _DOMAIN_RE.search(text)
        domain = domain_m.group(1).strip() if domain_m else ""

        clusters: list[dict[str, Any]] = []
        for cm in _CLUSTER_LINE_RE.finditer(text):
            clusters.append({
                "name": cm.group(1).strip(),
                "function": cm.group(2).strip(),
                "positions": int(cm.group(3)),
                "family": cm.group(4).strip(),
            })

        beings.append({
            "id": slug,
            "name": name,
            "acti_id": acti_id,
            "type": being_type,
            "positions": positions,
            "domain": domain,
            "levers": levers,
            "clusters": clusters,
            "sister_id": BEING_SISTER_MAP.get(slug, ""),
            "shared_heart_skills": [s["name"] for s in SHARED_HEART_SKILLS],
        })

    _cache["beings"] = beings
    return beings


def load_clusters(root: Path | None = None) -> list[dict[str, Any]]:
    """Load all 80 cluster definitions from the clusters/ subdirectories.

    Returns a list of dicts with keys:
        id, name, family, being, tier, positions, function, description
    """
    if "clusters" in _cache:
        return _cache["clusters"]

    root = root or _ACTI_ROOT
    clusters_dir = root / "clusters"
    if not clusters_dir.is_dir():
        return []

    clusters: list[dict[str, Any]] = []
    for family_dir in sorted(clusters_dir.iterdir()):
        if not family_dir.is_dir():
            continue
        for md_file in sorted(family_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            slug = md_file.stem
            name = text.split("\n", 1)[0].lstrip("# ").strip()

            family_m = _CLUSTER_FAMILY_RE.search(text)
            family = family_m.group(1).strip() if family_m else family_dir.name

            being_m = _CLUSTER_BEING_RE.search(text)
            being = being_m.group(1).strip() if being_m else ""

            tier_m = _CLUSTER_TIER_RE.search(text)
            tier = tier_m.group(1).strip() if tier_m else ""

            pos_m = _CLUSTER_POS_RE.search(text)
            positions = int(pos_m.group(1)) if pos_m else 0

            func_m = _CLUSTER_FUNC_RE.search(text)
            function = func_m.group(1).strip() if func_m else ""

            desc_m = _CLUSTER_DESC_RE.search(text)
            description = desc_m.group(1).strip() if desc_m else ""

            clusters.append({
                "id": slug,
                "name": name,
                "family": family,
                "being": being,
                "tier": tier,
                "positions": positions,
                "function": function,
                "description": description,
            })

    _cache["clusters"] = clusters
    return clusters


def load_skill_families(root: Path | None = None) -> list[dict[str, Any]]:
    """Load the 9 skill family definitions.

    Returns a list of dicts with keys:
        name, clusters_count, positions, key_beings
    """
    if "skill_families" in _cache:
        return _cache["skill_families"]

    root = root or _ACTI_ROOT
    sf_path = root / "skills" / "skill-families.md"
    if not sf_path.exists():
        return []

    text = sf_path.read_text(encoding="utf-8")
    families: list[dict[str, Any]] = []
    for m in _FAMILY_ROW_RE.finditer(text):
        name = m.group(1).strip()
        if name.lower() in ("family", "---"):
            continue
        families.append({
            "name": name,
            "clusters_count": int(m.group(2)),
            "positions": int(m.group(3).replace(",", "")),
            "key_beings": [b.strip() for b in m.group(4).split(",")],
        })

    _cache["skill_families"] = families
    return families


def load_lever_matrix(root: Path | None = None) -> dict[str, list[str]]:
    """Return a being_id -> list of lever IDs mapping.

    Parsed from the Being × Lever coverage matrix in levers.md.
    """
    if "lever_matrix" in _cache:
        return _cache["lever_matrix"]

    beings = load_beings(root)
    matrix: dict[str, list[str]] = {}
    for b in beings:
        if b["levers"]:
            matrix[b["id"]] = b["levers"]

    _cache["lever_matrix"] = matrix
    return matrix


# ── Aggregation helpers ──────────────────────────────────────────────────

def get_sister_profile(sister_id: str, root: Path | None = None) -> dict[str, Any]:
    """Aggregate ACT-I data for a specific runtime sister.

    Returns:
        beings: list of ACT-I beings mapped to this sister
        clusters: list of clusters owned by those beings
        levers: sorted list of unique lever IDs covered
        positions_total: total positions count
        shared_heart_skills: the 4 universal skills
    """
    beings = load_beings(root)
    all_clusters = load_clusters(root)

    sister_beings = [b for b in beings if b["sister_id"] == sister_id]
    being_names = {b["name"] for b in sister_beings}

    sister_clusters = [c for c in all_clusters if c["being"] in being_names]

    lever_set: set[str] = set()
    for b in sister_beings:
        lever_set.update(b["levers"])
    levers_sorted = sorted(lever_set, key=lambda x: float(x))

    positions_total = sum(b["positions"] for b in sister_beings)

    return {
        "beings": sister_beings,
        "clusters": sister_clusters,
        "levers": levers_sorted,
        "positions_total": positions_total,
        "shared_heart_skills": SHARED_HEART_SKILLS,
    }


def get_planning_context(root: Path | None = None) -> str:
    """Build a compact text summary of the ACT-I architecture for
    injection into the orchestration planning prompt.

    Includes: being→sister map, cluster inventory per sister, lever coverage.
    Kept under ~2000 chars to avoid bloating the planning prompt.
    """
    root = root or _ACTI_ROOT
    lines: list[str] = []
    lines.append("## ACT-I Architecture Reference")
    lines.append("")
    lines.append("17 operational beings + 2 apex, 80 clusters, 9 skill families, 7 levers.")
    lines.append("Each being is operated by a runtime sister.")
    lines.append("")

    for sid in ("prime", "scholar", "forge", "recovery"):
        profile = get_sister_profile(sid, root)
        being_names = [b["name"] for b in profile["beings"]]
        lines.append(
            f"**{sid.title()}** ({profile['positions_total']}p): "
            f"{', '.join(being_names)}"
        )
        # Top clusters by position count
        top_clusters = sorted(
            profile["clusters"], key=lambda c: c["positions"], reverse=True
        )[:5]
        if top_clusters:
            cluster_strs = [
                f"{c['name']} ({c['function']}, {c['positions']}p)"
                for c in top_clusters
            ]
            lines.append(f"  Top clusters: {', '.join(cluster_strs)}")
        lines.append(f"  Levers: {', '.join('L' + lv for lv in profile['levers'])}")
        lines.append("")

    return "\n".join(lines)


def get_full_architecture(root: Path | None = None) -> dict[str, Any]:
    """Return the complete architecture as a single dict for the dashboard."""
    root = root or _ACTI_ROOT
    beings = load_beings(root)
    clusters = load_clusters(root)
    families = load_skill_families(root)
    lever_matrix = load_lever_matrix(root)

    sister_profiles: dict[str, dict[str, Any]] = {}
    for sid in ("prime", "scholar", "forge", "recovery", "sai-memory"):
        sister_profiles[sid] = get_sister_profile(sid, root)

    return {
        "beings": beings,
        "clusters": clusters,
        "skill_families": families,
        "levers": LEVERS,
        "lever_matrix": lever_matrix,
        "sister_profiles": sister_profiles,
        "shared_heart_skills": SHARED_HEART_SKILLS,
        "being_sister_map": BEING_SISTER_MAP,
        "stats": {
            "total_beings": len(beings),
            "total_clusters": len(clusters),
            "total_positions": sum(b["positions"] for b in beings),
            "total_skill_families": len(families),
            "total_levers": len(LEVERS),
        },
    }
