"""Tests for the update_team_context tool and shared team context."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bomba_sr.tools.builtin_team_context import (
    builtin_team_context_tools,
    TEAM_CONTEXT_MAX_CHARS,
    _TEAM_CONTEXT_TEMPLATE,
    _resolve_team_context_path,
)
from bomba_sr.tools.base import ToolContext


def _make_context(workspace_root: Path, tenant_id: str = "tenant-prime") -> ToolContext:
    return ToolContext(
        tenant_id=tenant_id,
        session_id="sess-1",
        turn_id="turn-1",
        user_id="user-1",
        workspace_root=workspace_root,
        db=MagicMock(),
        guard_path=lambda p: Path(p),
    )


class TestUpdateTeamContextTool:
    def test_creates_file_if_missing(self, tmp_path):
        ctx = _make_context(tmp_path)
        tool = builtin_team_context_tools()[0]
        result = tool.execute({"section": "Active Priorities", "content": "Ship v2."}, ctx)
        assert result["status"] == "updated"
        # File created at parent (workspaces-level fallback)
        tc_path = _resolve_team_context_path(tmp_path)
        assert tc_path.exists()
        text = tc_path.read_text()
        assert "Ship v2." in text

    def test_updates_existing_section(self, tmp_path):
        tc = tmp_path / "TEAM_CONTEXT.md"
        tc.write_text(_TEAM_CONTEXT_TEMPLATE)
        ctx = _make_context(tmp_path)
        tool = builtin_team_context_tools()[0]
        tool.execute({"section": "Active Priorities", "content": "Launch beta."}, ctx)
        text = tc.read_text()
        assert "Launch beta." in text
        assert "## Recent Task Outcomes" in text
        assert "## Cross-Being Notes" in text

    def test_replaces_section_content(self, tmp_path):
        tc = tmp_path / "TEAM_CONTEXT.md"
        tc.write_text(
            "# Team Context\n\n## Active Priorities\nOld priority.\n\n## Cross-Being Notes\nNote.\n"
        )
        ctx = _make_context(tmp_path)
        tool = builtin_team_context_tools()[0]
        tool.execute({"section": "Active Priorities", "content": "New priority."}, ctx)
        text = tc.read_text()
        assert "New priority." in text
        assert "Old priority." not in text
        assert "Note." in text

    def test_enforces_size_cap(self, tmp_path):
        tc = tmp_path / "TEAM_CONTEXT.md"
        tc.write_text(_TEAM_CONTEXT_TEMPLATE)
        ctx = _make_context(tmp_path)
        tool = builtin_team_context_tools()[0]
        big = "x" * (TEAM_CONTEXT_MAX_CHARS + 500)
        result = tool.execute({"section": "Active Priorities", "content": big}, ctx)
        text = tc.read_text()
        assert len(text) <= TEAM_CONTEXT_MAX_CHARS
        assert result["total_chars"] <= TEAM_CONTEXT_MAX_CHARS

    def test_prime_only_gate_rejects_sister(self, tmp_path):
        tc = tmp_path / "TEAM_CONTEXT.md"
        tc.write_text(_TEAM_CONTEXT_TEMPLATE)
        ctx = _make_context(tmp_path, tenant_id="tenant-forge")
        tool = builtin_team_context_tools()[0]
        with pytest.raises(PermissionError, match="Only Prime"):
            tool.execute({"section": "Active Priorities", "content": "Nope."}, ctx)

    def test_prime_tenant_local_allowed(self, tmp_path):
        tc = tmp_path / "TEAM_CONTEXT.md"
        tc.write_text(_TEAM_CONTEXT_TEMPLATE)
        ctx = _make_context(tmp_path, tenant_id="tenant-local")
        tool = builtin_team_context_tools()[0]
        result = tool.execute({"section": "Active Priorities", "content": "Yes."}, ctx)
        assert result["status"] == "updated"

    def test_requires_section_and_content(self, tmp_path):
        ctx = _make_context(tmp_path)
        tool = builtin_team_context_tools()[0]
        with pytest.raises(ValueError, match="section and content are required"):
            tool.execute({"section": "", "content": "stuff"}, ctx)
        with pytest.raises(ValueError, match="section and content are required"):
            tool.execute({"section": "Active Priorities", "content": ""}, ctx)

    def test_tool_definition_shape(self):
        tools = builtin_team_context_tools()
        assert len(tools) == 1
        t = tools[0]
        assert t.name == "update_team_context"
        assert t.risk_level == "low"
        assert t.action_type == "write"
        assert "section" in t.parameters["properties"]
        assert "content" in t.parameters["properties"]


class TestResolveTeamContextPath:
    def test_finds_in_current_dir(self, tmp_path):
        (tmp_path / "TEAM_CONTEXT.md").write_text("# Team")
        assert _resolve_team_context_path(tmp_path) == tmp_path / "TEAM_CONTEXT.md"

    def test_finds_in_parent_dir(self, tmp_path):
        child = tmp_path / "forge"
        child.mkdir()
        (tmp_path / "TEAM_CONTEXT.md").write_text("# Team")
        assert _resolve_team_context_path(child) == tmp_path / "TEAM_CONTEXT.md"

    def test_defaults_to_parent_when_missing(self, tmp_path):
        child = tmp_path / "forge"
        child.mkdir()
        result = _resolve_team_context_path(child)
        assert result == tmp_path / "TEAM_CONTEXT.md"
