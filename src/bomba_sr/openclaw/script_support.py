from __future__ import annotations

import os
from pathlib import Path


def repo_root(start: str | Path | None = None) -> Path:
    probes: list[Path] = []
    if start is not None:
        probes.append(Path(start).expanduser().resolve())
    probes.append(Path(__file__).resolve())
    for probe in probes:
        current = probe if probe.is_dir() else probe.parent
        for parent in (current, *current.parents):
            if (parent / "pyproject.toml").is_file() and (parent / "workspaces").is_dir():
                return parent
    return Path(__file__).resolve().parents[3]


def portable_home(start: str | Path | None = None) -> Path:
    return repo_root(start) / ".portable-home"


def bundled_openclaw_home(start: str | Path | None = None) -> Path:
    return repo_root(start) / "portable-openclaw"


def env_candidates(start: str | Path | None = None) -> list[Path]:
    repo = repo_root(start)
    explicit = os.getenv("OPENCLAW_ENV_FILE", "").strip()
    candidates = [
        Path(explicit).expanduser() if explicit else None,
        repo / ".env",
        bundled_openclaw_home(repo) / ".env",
        portable_home(repo) / ".openclaw" / ".env",
        Path.home() / ".openclaw" / ".env",
    ]
    return [path for path in candidates if path is not None]


def load_portable_env(start: str | Path | None = None, *, override: bool = False) -> Path | None:
    for env_path in env_candidates(start):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            if raw.startswith("export "):
                raw = raw[len("export "):].strip()
            if "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (override or key not in os.environ or not os.environ.get(key)):
                os.environ[key] = value
        return env_path
    return None


def workspace_dir(workspace_name: str, start: str | Path | None = None) -> Path:
    return repo_root(start) / "workspaces" / workspace_name
