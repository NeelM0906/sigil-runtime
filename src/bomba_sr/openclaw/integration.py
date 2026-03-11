from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKSPACES_ROOT = _REPO_ROOT / "workspaces"
_BUNDLED_OPENCLAW_ROOT = _REPO_ROOT / "portable-openclaw"
_PORTABLE_HOME_ROOT = _REPO_ROOT / ".portable-home"
_DEFAULT_WORKSPACES = {
    "main": _WORKSPACES_ROOT / "prime",
    "forge": _WORKSPACES_ROOT / "forge",
    "scholar": _WORKSPACES_ROOT / "scholar",
    "memory": _WORKSPACES_ROOT / "sai-memory",
    "recovery": _WORKSPACES_ROOT / "recovery",
}
_WORKSPACE_PROJECT_EXCLUDES = {"memory", "tools", "skills", "configs", "agents", "__pycache__"}
_PORTABLE_WORKSPACE_LINKS = {
    "workspace": _WORKSPACES_ROOT / "prime",
    "workspace-forge": _WORKSPACES_ROOT / "forge",
    "workspace-scholar": _WORKSPACES_ROOT / "scholar",
    "workspace-memory": _WORKSPACES_ROOT / "sai-memory",
}
_PORTABLE_RECOVERY_LINK = _WORKSPACES_ROOT / "recovery"
_OPENCLAW_USER_PATH_RE = re.compile(r"/Users/[^/\s]+/\.openclaw")
_OPENCLAW_HOME_PATH_RE = re.compile(r"/home/[^/\s]+/\.openclaw")


def _external_sync_requested() -> bool:
    return os.getenv("BOMBA_ENABLE_EXTERNAL_SYNC", "").lower() in {"1", "true", "yes"} or bool(
        os.getenv("BOMBA_OPENCLAW_SOURCE_ROOT", "").strip()
    )


def repo_root() -> Path:
    return _REPO_ROOT


def sanitize_portable_text(text: str, root: str | Path | None = None) -> str:
    cleaned = text or ""
    repo = discover_repo_root(root)
    repo_str = str(repo.resolve())
    if repo_str in cleaned:
        cleaned = cleaned.replace(repo_str, ".")
    home = os.path.expanduser("~").rstrip("/")
    if home:
        cleaned = cleaned.replace(home, "~")
    cleaned = _OPENCLAW_USER_PATH_RE.sub("~/.openclaw", cleaned)
    cleaned = _OPENCLAW_HOME_PATH_RE.sub("~/.openclaw", cleaned)
    return cleaned


def portable_display_path(path: str | Path | None, root: str | Path | None = None) -> str:
    if path is None:
        return ""
    candidate = Path(str(path)).expanduser()
    repo = discover_repo_root(root)
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate
    try:
        return str(resolved.relative_to(repo))
    except ValueError:
        return sanitize_portable_text(str(resolved), repo)


def discover_repo_root(start: str | Path | None = None) -> Path:
    probes: list[Path] = []
    if start is not None:
        probes.append(Path(start).expanduser().resolve())
    probes.append(Path(__file__).resolve())
    for probe in probes:
        current = probe if probe.is_dir() else probe.parent
        for parent in (current, *current.parents):
            if (parent / "pyproject.toml").is_file() and (parent / "workspaces").is_dir():
                return parent
    return _REPO_ROOT


def bundled_openclaw_root(root: str | Path | None = None) -> Path:
    return discover_repo_root(root) / "portable-openclaw"


def portable_home_root(root: str | Path | None = None) -> Path:
    return discover_repo_root(root) / ".portable-home"


def is_bundled_openclaw_root(path: str | Path | None) -> bool:
    if path is None:
        return False
    candidate = Path(path).expanduser().resolve()
    return candidate == bundled_openclaw_root(candidate)


def _resolve_openclaw_root(root: str | Path | None = None) -> Path | None:
    if root is not None:
        candidate = Path(root).expanduser().resolve()
        if candidate.is_dir() and (candidate / "openclaw.json").is_file():
            return candidate
    return discover_openclaw_root(root)


def _ensure_relative_symlink(link_path: Path, target_path: Path) -> None:
    target = target_path.expanduser().resolve()
    if not target.exists():
        return
    if link_path.is_symlink():
        try:
            if link_path.resolve() == target:
                return
        except OSError:
            pass
        link_path.unlink()
    elif link_path.exists():
        return
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(os.path.relpath(target, link_path.parent), target_is_directory=target.is_dir())


def _rewrite_bundled_openclaw_config(openclaw_root: Path) -> None:
    config_path = openclaw_root / "openclaw.json"
    if not config_path.is_file():
        return
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    agents = payload.setdefault("agents", {})
    if not isinstance(agents, dict):
        return
    defaults = agents.setdefault("defaults", {})
    if isinstance(defaults, dict):
        defaults["workspace"] = "./workspace"
    items = agents.get("list")
    if isinstance(items, list):
        workspace_map = {
            "main": "./workspace",
            "forge": "./workspace-forge",
            "scholar": "./workspace-scholar",
            "memory": "./workspace-memory",
            "recovery": "./workspace/sisters/sai-recovery",
        }
        agent_dir_map = {
            "main": "./agents/main/agent",
            "forge": "./agents/forge/agent",
            "scholar": "./agents/scholar/agent",
            "memory": "./agents/memory/agent",
            "recovery": "./agents/recovery/agent",
        }
        for item in items:
            if not isinstance(item, dict):
                continue
            agent_id = str(item.get("id") or "").strip()
            target = workspace_map.get(agent_id)
            if target is not None:
                item["workspace"] = target
            agent_dir = agent_dir_map.get(agent_id)
            if agent_dir is not None:
                item["agentDir"] = agent_dir
    config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def ensure_portable_openclaw_layout(root: str | Path | None = None) -> Path:
    repo = discover_repo_root(root)
    openclaw_root = bundled_openclaw_root(repo)
    portable_home = portable_home_root(repo)
    openclaw_root.mkdir(parents=True, exist_ok=True)

    for link_name, target in _PORTABLE_WORKSPACE_LINKS.items():
        _ensure_relative_symlink(openclaw_root / link_name, target)
    (openclaw_root / "workspace" / "sisters").mkdir(parents=True, exist_ok=True)
    _ensure_relative_symlink(openclaw_root / "workspace" / "sisters" / "sai-recovery", _PORTABLE_RECOVERY_LINK)

    if (repo / ".env").exists():
        _ensure_relative_symlink(openclaw_root / ".env", repo / ".env")
        for workspace_name in ("prime", "forge", "scholar", "sai-memory", "recovery"):
            _ensure_relative_symlink(repo / "workspaces" / workspace_name / ".env", repo / ".env")
    if (repo / ".venv").exists():
        _ensure_relative_symlink(openclaw_root / ".venv", repo / ".venv")
        for workspace_name in ("prime", "forge", "scholar", "sai-memory", "recovery"):
            _ensure_relative_symlink(repo / "workspaces" / workspace_name / "tools" / ".venv", repo / ".venv")

    (openclaw_root / "credentials").mkdir(parents=True, exist_ok=True)
    (openclaw_root / "media" / "inbound").mkdir(parents=True, exist_ok=True)
    (portable_home / ".openclaw").parent.mkdir(parents=True, exist_ok=True)
    _ensure_relative_symlink(portable_home / ".openclaw", openclaw_root)
    _rewrite_bundled_openclaw_config(openclaw_root)
    return openclaw_root


def discover_openclaw_root(start: str | Path | None = None) -> Path | None:
    if not _external_sync_requested():
        return None

    explicit = os.getenv("BOMBA_OPENCLAW_SOURCE_ROOT", "").strip()
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.is_dir() else None

    probes: list[Path] = []
    if start is not None:
        probes.append(Path(start).expanduser().resolve())
    probes.append(Path(__file__).resolve())

    for probe in probes:
        current = probe if probe.is_dir() else probe.parent
        for parent in (current, *current.parents):
            if (parent / "openclaw.json").is_file():
                return parent
    return None


def load_openclaw_config(root: str | Path | None = None) -> dict[str, Any]:
    resolved_root = _resolve_openclaw_root(root)
    if resolved_root is None:
        return {}
    config_path = resolved_root / "openclaw.json"
    if not config_path.is_file():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def list_agent_workspaces(root: str | Path | None = None) -> dict[str, Path]:
    external_root = _resolve_openclaw_root(root)
    if external_root is not None:
        if is_bundled_openclaw_root(external_root):
            repo = discover_repo_root(external_root)
            bundled_workspaces = {
                "main": repo / "workspaces" / "prime",
                "forge": repo / "workspaces" / "forge",
                "scholar": repo / "workspaces" / "scholar",
                "memory": repo / "workspaces" / "sai-memory",
                "recovery": repo / "workspaces" / "recovery",
            }
            return {
                agent_id: workspace.resolve()
                for agent_id, workspace in bundled_workspaces.items()
                if workspace.is_dir()
            }
        config = load_openclaw_config(external_root)
        defaults = (config.get("agents", {}) or {}).get("defaults", {}) or {}
        default_workspace = str(defaults.get("workspace") or (external_root / "workspace"))
        workspaces: dict[str, Path] = {
            "main": Path(default_workspace).expanduser().resolve(),
            "forge": (external_root / "workspace-forge").resolve(),
            "scholar": (external_root / "workspace-scholar").resolve(),
            "memory": (external_root / "workspace-memory").resolve(),
            "recovery": (external_root / "workspace" / "sisters" / "sai-recovery").resolve(),
        }
        for item in (config.get("agents", {}) or {}).get("list", []):
            if not isinstance(item, dict):
                continue
            agent_id = str(item.get("id") or "").strip()
            raw_workspace = str(item.get("workspace") or "").strip()
            if agent_id and raw_workspace:
                workspaces[agent_id] = Path(raw_workspace).expanduser().resolve()
        return workspaces

    return {
        agent_id: workspace.resolve()
        for agent_id, workspace in _DEFAULT_WORKSPACES.items()
        if workspace.is_dir()
    }


def list_skill_roots(workspace_root: str | Path | None = None) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.expanduser().resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            return
        seen.add(resolved)
        roots.append(resolved)

    if workspace_root is not None:
        add(Path(workspace_root) / "skills")

    for agent_workspace in list_agent_workspaces(workspace_root).values():
        add(agent_workspace / "skills")

    add(_REPO_ROOT / "skills")

    extra_roots = os.getenv("BOMBA_EXTRA_SKILL_ROOTS", "").strip()
    if extra_roots:
        for raw in extra_roots.replace(";", ":").split(":"):
            if raw.strip():
                add(Path(raw.strip()))
    return roots


def discover_colosseum_data_roots(anchor: str | Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.expanduser().resolve()
        if resolved in seen or not resolved.is_dir():
            return
        required = (
            resolved / "v2" / "data" / "beings.json",
            resolved / "v2" / "data" / "judges.json",
            resolved / "v2" / "data" / "scenarios.json",
        )
        if not all(item.is_file() for item in required):
            return
        seen.add(resolved)
        candidates.append(resolved)

    if anchor is not None:
        anchor_path = Path(anchor).expanduser().resolve()
        add(anchor_path)
        add(anchor_path / "Projects" / "colosseum")
        add(anchor_path / "colosseum")

    bundled_main = _WORKSPACES_ROOT / "prime"
    bundled_forge = _WORKSPACES_ROOT / "forge"
    add(bundled_main / "Projects" / "colosseum")
    add(bundled_main / "colosseum")
    add(bundled_forge / "colosseum")

    external_root = _resolve_openclaw_root(anchor)
    if external_root is not None:
        add(external_root / "workspace")
        add(external_root / "workspace" / "Projects" / "colosseum")
        add(external_root / "workspace" / "colosseum")
        add(external_root / "workspace-forge" / "colosseum")

    return candidates


def list_project_inventory(root: str | Path | None = None) -> list[dict[str, Any]]:
    external_root = discover_openclaw_root(root)
    inventory_root = external_root if external_root is not None else _REPO_ROOT
    workspaces = list_agent_workspaces(root)

    items: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    def add(path: Path, *, project_id: str, name: str, kind: str, workspace_id: str | None, tags: list[str]) -> None:
        resolved = path.expanduser().resolve()
        if resolved in seen_paths or not resolved.exists():
            return
        seen_paths.add(resolved)
        items.append({
            "id": project_id,
            "name": name,
            "kind": kind,
            "workspace_id": workspace_id,
            "path": str(resolved),
            "relative_path": _relative_path(resolved, inventory_root),
            "tags": sorted(set(tags)),
            "summary": _project_summary(resolved),
            "entrypoints": _project_entrypoints(resolved),
            "last_modified": datetime.fromtimestamp(
                resolved.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(),
        })

    for agent_id, workspace in workspaces.items():
        workspace_name = {
            "main": "Prime Workspace",
            "forge": "Forge Workspace",
            "scholar": "Scholar Workspace",
            "memory": "Memory Workspace",
            "recovery": "Recovery Workspace",
        }.get(agent_id, f"{agent_id.title()} Workspace")
        add(
            workspace,
            project_id=f"workspace-{agent_id}",
            name=workspace_name,
            kind="workspace",
            workspace_id=agent_id,
            tags=["workspace", agent_id],
        )
        _scan_workspace_projects(add, workspace, workspace_id=agent_id)

    add(_REPO_ROOT / "mission-control", project_id="mission-control", name="Mission Control Dashboard", kind="dashboard", workspace_id=None, tags=["dashboard", "mission-control"])
    add(_REPO_ROOT / "skills", project_id="shared-skills", name="Shared Skills Library", kind="library", workspace_id=None, tags=["skills", "library"])

    items.sort(key=lambda item: (0 if "colosseum" in item["tags"] else 1, item["name"].lower()))
    return items


def _scan_workspace_projects(add, workspace: Path, *, workspace_id: str) -> None:
    if not workspace.is_dir():
        return

    projects_dir = workspace / "Projects"
    if projects_dir.is_dir():
        for entry in sorted(projects_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                tags = ["project", entry.name.lower()]
                kind = "colosseum" if entry.name.lower() == "colosseum" else "project"
                add(
                    entry,
                    project_id=f"{workspace_id}-project-{entry.name}",
                    name=_display_name(entry.name),
                    kind=kind,
                    workspace_id=workspace_id,
                    tags=tags,
                )

    for entry in sorted(workspace.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in _WORKSPACE_PROJECT_EXCLUDES:
            continue
        lower = entry.name.lower()
        tags = [workspace_id]
        if "colosseum" in lower:
            kind = "colosseum" if "dashboard" not in lower else "dashboard"
            tags.extend(["colosseum", "dashboard" if "dashboard" in lower else "tournament"])
        else:
            kind = "project"
            tags.append("project")
        add(
            entry,
            project_id=f"{workspace_id}-{entry.name}",
            name=_display_name(entry.name),
            kind=kind,
            workspace_id=workspace_id,
            tags=tags,
        )


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _display_name(name: str) -> str:
    parts = name.replace("_", "-").split("-")
    return " ".join(part.capitalize() for part in parts if part)


def _project_summary(path: Path) -> str:
    candidates = ("README.md", "README", "README.txt", "MISSION.md", "OVERVIEW.md")
    for name in candidates:
        candidate = path / name
        if candidate.is_file():
            try:
                lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    return stripped[:220]
    return ""


def _project_entrypoints(path: Path) -> list[str]:
    entries: list[str] = []
    for name in (
        "README.md",
        "package.json",
        "requirements.txt",
        "server.py",
        "run_server.py",
        "index.html",
        "dashboard.html",
        "battle-arena.html",
        "email-colosseum.html",
    ):
        candidate = path / name
        if candidate.exists():
            entries.append(candidate.name)
    return entries
