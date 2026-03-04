"""Tests for input validation guards that prevent prompt injection into tools."""
from __future__ import annotations

import pytest

from bomba_sr.codeintel.base import CodeIntelError
from bomba_sr.codeintel.native import _validate_symbol_name
from bomba_sr.tools.base import _LARGE_VALUE_PARAMS, _MAX_PARAM_VALUE_LEN


class TestSymbolNameValidation:
    """Level 1: codeintel/native.py rejects nonsense symbol names."""

    def test_valid_simple_name(self):
        assert _validate_symbol_name("RuntimeBridge") == "RuntimeBridge"

    def test_valid_dotted_name(self):
        assert _validate_symbol_name("bomba_sr.runtime.bridge") == "bomba_sr.runtime.bridge"

    def test_valid_name_with_dollar(self):
        assert _validate_symbol_name("$scope") == "$scope"

    def test_valid_name_with_slash(self):
        assert _validate_symbol_name("Foo/bar") == "Foo/bar"

    def test_rejects_empty(self):
        with pytest.raises(CodeIntelError, match="required"):
            _validate_symbol_name("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(CodeIntelError, match="required"):
            _validate_symbol_name("   ")

    def test_rejects_multiline(self):
        with pytest.raises(CodeIntelError, match="multi-line"):
            _validate_symbol_name("line1\nline2")

    def test_rejects_too_long(self):
        with pytest.raises(CodeIntelError, match="max 200"):
            _validate_symbol_name("a" * 201)

    def test_rejects_brackets(self):
        with pytest.raises(CodeIntelError, match="alphanumeric"):
            _validate_symbol_name("find_symbol(args)")

    def test_rejects_curly_braces(self):
        with pytest.raises(CodeIntelError, match="alphanumeric"):
            _validate_symbol_name('{"tool": "find_symbol"}')

    def test_rejects_prompt_text(self):
        prompt = (
            "[SYSTEM: ORCHESTRATION MODE] You are SAI Prime. "
            "Decompose this task into sub-tasks for the available beings."
        )
        with pytest.raises(CodeIntelError, match="alphanumeric"):
            _validate_symbol_name(prompt)

    def test_rejects_delegation_message(self):
        msg = (
            "You have been assigned a sub-task by SAI Prime.\n\n"
            "TASK TITLE: Search Pinecone indexes\n\n"
            "INSTRUCTIONS:\nSearch all indexes for content."
        )
        with pytest.raises(CodeIntelError, match="multi-line"):
            _validate_symbol_name(msg)


class TestToolExecutorParamGuard:
    """Level 3: ToolExecutor rejects mega-strings in non-content params."""

    def test_large_value_params_are_exempted(self):
        assert "content" in _LARGE_VALUE_PARAMS
        assert "body" in _LARGE_VALUE_PARAMS
        assert "new_body" in _LARGE_VALUE_PARAMS
        assert "text" in _LARGE_VALUE_PARAMS

    def test_max_param_value_len_is_reasonable(self):
        assert _MAX_PARAM_VALUE_LEN == 500

    def test_search_params_not_exempted(self):
        for name in ("symbol_name", "query", "pattern", "search_term", "old_name"):
            assert name not in _LARGE_VALUE_PARAMS
