"""Tests for the update_knowledge tool and cross-namespace recall."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bomba_sr.tools.builtin_knowledge import (
    builtin_knowledge_tools,
    KNOWLEDGE_MAX_CHARS,
    _KNOWLEDGE_TEMPLATE,
)
from bomba_sr.tools.base import ToolContext


def _make_context(workspace_root: Path) -> ToolContext:
    return ToolContext(
        tenant_id="t-test",
        session_id="sess-1",
        turn_id="turn-1",
        user_id="user-1",
        workspace_root=workspace_root,
        db=MagicMock(),
        guard_path=lambda p: Path(p),
    )


class TestUpdateKnowledgeTool:
    def test_creates_file_if_missing(self, tmp_path):
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        result = tool.execute({"section": "Key Facts", "content": "The sky is blue."}, ctx)
        assert result["status"] == "updated"
        assert (tmp_path / "KNOWLEDGE.md").exists()
        text = (tmp_path / "KNOWLEDGE.md").read_text()
        assert "The sky is blue." in text

    def test_updates_existing_section(self, tmp_path):
        kb = tmp_path / "KNOWLEDGE.md"
        kb.write_text(_KNOWLEDGE_TEMPLATE)
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        tool.execute({"section": "Domain Expertise", "content": "Expert in Python."}, ctx)
        text = kb.read_text()
        assert "Expert in Python." in text
        # Other sections should still exist
        assert "## Key Facts" in text
        assert "## Learned Patterns" in text

    def test_replaces_section_content(self, tmp_path):
        kb = tmp_path / "KNOWLEDGE.md"
        kb.write_text("# KB\n\n## Key Facts\nOld fact.\n\n## Domain Expertise\nOld expertise.\n")
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        tool.execute({"section": "Key Facts", "content": "New fact."}, ctx)
        text = kb.read_text()
        assert "New fact." in text
        assert "Old fact." not in text
        # Other section untouched
        assert "Old expertise." in text

    def test_adds_new_section(self, tmp_path):
        kb = tmp_path / "KNOWLEDGE.md"
        kb.write_text(_KNOWLEDGE_TEMPLATE)
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        tool.execute({"section": "Custom Section", "content": "Custom content."}, ctx)
        text = kb.read_text()
        assert "## Custom Section" in text
        assert "Custom content." in text

    def test_enforces_size_cap(self, tmp_path):
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        big_content = "x" * (KNOWLEDGE_MAX_CHARS + 500)
        result = tool.execute({"section": "Key Facts", "content": big_content}, ctx)
        text = (tmp_path / "KNOWLEDGE.md").read_text()
        assert len(text) <= KNOWLEDGE_MAX_CHARS
        assert result["total_chars"] <= KNOWLEDGE_MAX_CHARS

    def test_requires_section_and_content(self, tmp_path):
        ctx = _make_context(tmp_path)
        tool = builtin_knowledge_tools()[0]
        with pytest.raises(ValueError, match="section and content are required"):
            tool.execute({"section": "", "content": "stuff"}, ctx)
        with pytest.raises(ValueError, match="section and content are required"):
            tool.execute({"section": "Key Facts", "content": ""}, ctx)

    def test_tool_definition_shape(self):
        tools = builtin_knowledge_tools()
        assert len(tools) == 1
        t = tools[0]
        assert t.name == "update_knowledge"
        assert t.risk_level == "low"
        assert t.action_type == "write"
        assert "section" in t.parameters["properties"]
        assert "content" in t.parameters["properties"]
