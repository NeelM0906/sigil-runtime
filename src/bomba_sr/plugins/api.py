from __future__ import annotations

from pathlib import Path
from typing import Any


class PluginAPI:
    """Plugin extension API (v1 scope: tools + skill dirs)."""

    def __init__(self, plugin_id: str, registry: Any, config: dict[str, Any]):
        self.plugin_id = plugin_id
        self._registry = registry
        self.config = config

    def register_tool(self, tool: Any) -> None:
        self._registry._register_plugin_tool(self.plugin_id, tool)

    def register_skill_dir(self, path: Path) -> None:
        self._registry._register_plugin_skill_dir(self.plugin_id, path)
