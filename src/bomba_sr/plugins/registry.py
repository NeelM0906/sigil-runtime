from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from bomba_sr.plugins.api import PluginAPI


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    entry_module: str
    config_schema: dict[str, Any] | None
    kind: str | None
    skills_dir: str | None
    root_dir: Path


@dataclass
class _LoadedPlugin:
    manifest: PluginManifest
    module: ModuleType
    enabled: bool
    tools: list[Any]
    skill_dirs: list[Path]


class PluginRegistry:
    def __init__(
        self,
        allow: tuple[str, ...] = (),
        deny: tuple[str, ...] = (),
        config: dict[str, Any] | None = None,
    ) -> None:
        self.allow = set(x.strip() for x in allow if x.strip())
        self.deny = set(x.strip() for x in deny if x.strip())
        self.config = config or {}
        self._plugins: dict[str, _LoadedPlugin] = {}

    def discover(self, paths: list[Path]) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        for base in paths:
            root = base.expanduser().resolve()
            if not root.exists():
                continue
            for manifest_path in self._manifest_paths(root):
                try:
                    manifests.append(self._read_manifest(manifest_path))
                except Exception:
                    continue

        filtered: list[PluginManifest] = []
        for manifest in manifests:
            if manifest.plugin_id in self.deny:
                continue
            if self.allow and manifest.plugin_id not in self.allow:
                continue
            filtered.append(manifest)
        return filtered

    def load(self, manifest: PluginManifest) -> None:
        module = self._load_module(manifest)
        state = _LoadedPlugin(
            manifest=manifest,
            module=module,
            enabled=True,
            tools=[],
            skill_dirs=[],
        )
        self._plugins[manifest.plugin_id] = state

        api = PluginAPI(
            plugin_id=manifest.plugin_id,
            registry=self,
            config=self.config.get(manifest.plugin_id, {}) if isinstance(self.config, dict) else {},
        )

        register = getattr(module, "register", None)
        if callable(register):
            register(api)

        if manifest.skills_dir:
            skills_dir = (manifest.root_dir / manifest.skills_dir).resolve()
            if skills_dir.exists() and skills_dir.is_dir():
                state.skill_dirs.append(skills_dir)

    def enable(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"plugin not loaded: {plugin_id}")
        plugin.enabled = True

    def disable(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"plugin not loaded: {plugin_id}")
        plugin.enabled = False

    def get_tools(self) -> list[Any]:
        tools: list[Any] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            tools.extend(plugin.tools)
        return tools

    def get_skill_dirs(self) -> list[Path]:
        out: list[Path] = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            out.extend(plugin.skill_dirs)
        return out

    def _register_plugin_tool(self, plugin_id: str, tool: Any) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"plugin not loaded: {plugin_id}")
        plugin.tools.append(tool)

    def _register_plugin_skill_dir(self, plugin_id: str, path: Path) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"plugin not loaded: {plugin_id}")
        plugin.skill_dirs.append(path.expanduser().resolve())

    @staticmethod
    def _manifest_paths(root: Path) -> list[Path]:
        if root.is_file() and root.name == "bomba.plugin.json":
            return [root]
        if root.is_dir():
            direct = root / "bomba.plugin.json"
            if direct.exists():
                return [direct]
            out: list[Path] = []
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                candidate = child / "bomba.plugin.json"
                if candidate.exists():
                    out.append(candidate)
            return out
        return []

    @staticmethod
    def _read_manifest(path: Path) -> PluginManifest:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"invalid plugin manifest: {path}")

        plugin_id = str(payload.get("plugin_id") or payload.get("id") or "").strip()
        if not plugin_id:
            raise ValueError(f"plugin manifest missing plugin_id: {path}")

        entry_module = str(payload.get("entry_module") or payload.get("entry") or "").strip()
        if not entry_module:
            raise ValueError(f"plugin manifest missing entry_module: {path}")

        config_schema = payload.get("config_schema")
        if config_schema is not None and not isinstance(config_schema, dict):
            raise ValueError(f"plugin config_schema must be object: {path}")

        kind = payload.get("kind")
        skills_dir = payload.get("skills_dir")

        return PluginManifest(
            plugin_id=plugin_id,
            name=str(payload.get("name") or plugin_id),
            version=str(payload.get("version") or "0.0.0"),
            entry_module=entry_module,
            config_schema=config_schema,
            kind=(str(kind) if kind is not None else None),
            skills_dir=(str(skills_dir) if skills_dir is not None else None),
            root_dir=path.parent.resolve(),
        )

    @staticmethod
    def _load_module(manifest: PluginManifest) -> ModuleType:
        entry = manifest.entry_module
        if entry.endswith(".py") or "/" in entry or entry.startswith("."):
            module_path = (manifest.root_dir / entry).resolve()
            if not module_path.exists():
                raise ValueError(f"plugin entry module not found: {module_path}")
            spec = importlib.util.spec_from_file_location(f"bomba_plugin_{manifest.plugin_id}", module_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"unable to load plugin module: {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return importlib.import_module(entry)
