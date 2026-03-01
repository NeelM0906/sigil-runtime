from __future__ import annotations

import io
import json
import os
import unittest

from bomba_sr.cli.renderers import (
    CollapsedBlock,
    CollapsedTurnState,
    Theme,
    _format_code_search,
    _format_edit,
    _format_exec,
    _format_generic,
    _format_glob,
    _format_grep,
    _format_read,
    _format_write,
    build_collapsed_state,
    render_collapsed,
)


class FormatGlobTests(unittest.TestCase):
    def test_collapsed_with_more_indicator(self) -> None:
        files = [f"src/file_{i}.py" for i in range(20)]
        summary, preview, full, total = _format_glob({"files": files})
        self.assertEqual(total, 20)
        self.assertEqual(len(preview), 5)
        self.assertEqual(len(full), 20)
        self.assertIn("20 file(s)", summary)

    def test_empty_glob(self) -> None:
        summary, preview, full, total = _format_glob({"files": []})
        self.assertEqual(total, 0)
        self.assertEqual(preview, [])
        self.assertIn("0 file(s)", summary)


class FormatGrepTests(unittest.TestCase):
    def test_collapsed_with_more_indicator(self) -> None:
        matches = [{"path": f"src/f{i}.py", "line": i, "snippet": f"line {i}"} for i in range(30)]
        summary, preview, full, total = _format_grep({"matches": matches})
        self.assertEqual(total, 30)
        self.assertEqual(len(preview), 5)
        self.assertIn("30 match(es)", summary)

    def test_preview_contains_path_and_line(self) -> None:
        matches = [{"path": "src/foo.py", "line": 42, "snippet": "def bar():"}]
        _, preview, _, _ = _format_grep({"matches": matches})
        self.assertEqual(len(preview), 1)
        self.assertIn("src/foo.py:42", preview[0])
        self.assertIn("def bar():", preview[0])


class FormatCodeSearchTests(unittest.TestCase):
    def test_collapsed_with_confidence(self) -> None:
        results = [
            {"path": f"src/f{i}.py", "line_start": i, "confidence": 0.85}
            for i in range(10)
        ]
        summary, preview, full, total = _format_code_search(
            {"results": results, "avg_confidence": 0.85}
        )
        self.assertEqual(total, 10)
        self.assertEqual(len(preview), 5)
        self.assertIn("10 result(s)", summary)
        self.assertIn("0.85", summary)


class FormatReadTests(unittest.TestCase):
    def test_summary_only_no_collapse(self) -> None:
        summary, preview, full, total = _format_read(
            {"path": "src/foo.py", "lines": 100, "returned_lines": 50}
        )
        self.assertIn("src/foo.py", summary)
        self.assertIn("50/100", summary)
        self.assertEqual(total, 0)
        self.assertEqual(preview, [])
        self.assertEqual(full, [])


class FormatWriteTests(unittest.TestCase):
    def test_summary_only(self) -> None:
        summary, preview, full, total = _format_write(
            {"path": "out.txt", "bytes": 1024}
        )
        self.assertIn("out.txt", summary)
        self.assertIn("1024 bytes", summary)
        self.assertEqual(total, 0)


class FormatExecTests(unittest.TestCase):
    def test_collapsed_with_stdout(self) -> None:
        stdout = "\n".join(f"line {i}" for i in range(15))
        summary, preview, full, total = _format_exec(
            {"command": "ls -la", "exit_code": 0, "stdout": stdout, "stderr": ""}
        )
        self.assertIn("ls -la", summary)
        self.assertIn("exit 0", summary)
        self.assertEqual(total, 15)
        self.assertEqual(len(preview), 5)

    def test_long_command_truncated(self) -> None:
        cmd = "a" * 100
        summary, _, _, _ = _format_exec({"command": cmd, "exit_code": 0, "stdout": "", "stderr": ""})
        self.assertIn("...", summary)
        self.assertLess(len(summary), 200)


class FormatErrorStatusTests(unittest.TestCase):
    def test_error_tool_call_renders(self) -> None:
        tc = {
            "tool_call_id": "call-1",
            "tool_name": "glob",
            "status": "error",
            "output": {"error": "permission denied"},
            "risk_class": "low",
            "duration_ms": 5,
        }
        state = build_collapsed_state({"assistant": {"text": "oops", "tool_calls": [tc]}})
        self.assertEqual(len(state.blocks), 1)
        self.assertEqual(state.blocks[0].status, "error")


class FormatGenericTests(unittest.TestCase):
    def test_generic_json_preview(self) -> None:
        output = {"key1": "value1", "key2": [1, 2, 3], "key3": {"nested": True}}
        summary, preview, full, total = _format_generic("custom_tool", output)
        self.assertIn("custom_tool", summary)
        self.assertGreater(total, 0)
        self.assertLessEqual(len(preview), 5)


class AnsiDisabledTests(unittest.TestCase):
    def test_no_ansi_on_dumb_terminal(self) -> None:
        theme = Theme(color=False)
        self.assertEqual(theme.BOLD, "")
        self.assertEqual(theme.CYAN, "")
        self.assertEqual(theme.RESET, "")

    def test_ansi_enabled(self) -> None:
        theme = Theme(color=True)
        self.assertIn("\033[", theme.BOLD)
        self.assertIn("\033[", theme.CYAN)


class CollapsedTurnStateTests(unittest.TestCase):
    def test_has_collapsed_blocks_true(self) -> None:
        block = CollapsedBlock(
            index=0, tool_name="glob", tool_call_id="c1", status="executed",
            duration_ms=10, risk_class="low", summary_line="glob: 20 file(s)",
            preview_lines=["f1", "f2", "f3", "f4", "f5"],
            total_items=20, full_lines=[f"f{i}" for i in range(20)],
            raw_output={},
        )
        state = CollapsedTurnState(blocks=[block], assistant_text="test")
        self.assertTrue(state.has_collapsed_blocks)

    def test_has_collapsed_blocks_false(self) -> None:
        block = CollapsedBlock(
            index=0, tool_name="read", tool_call_id="c1", status="executed",
            duration_ms=2, risk_class="low", summary_line="read: foo.py",
            preview_lines=[], total_items=0, full_lines=[], raw_output={},
        )
        state = CollapsedTurnState(blocks=[block], assistant_text="test")
        self.assertFalse(state.has_collapsed_blocks)


class BuildFromTurnResultTests(unittest.TestCase):
    def test_full_integration(self) -> None:
        result = {
            "assistant": {
                "text": "Found the files.",
                "tool_calls": [
                    {
                        "tool_call_id": "c1",
                        "tool_name": "glob",
                        "status": "executed",
                        "output": {"files": [f"src/f{i}.py" for i in range(12)]},
                        "risk_class": "low",
                        "duration_ms": 23,
                    },
                    {
                        "tool_call_id": "c2",
                        "tool_name": "read",
                        "status": "executed",
                        "output": {"path": "src/main.py", "content": "x", "lines": 50, "returned_lines": 50},
                        "risk_class": "low",
                        "duration_ms": 2,
                    },
                ],
            }
        }
        state = build_collapsed_state(result)
        self.assertEqual(len(state.blocks), 2)
        self.assertEqual(state.blocks[0].tool_name, "glob")
        self.assertEqual(state.blocks[0].total_items, 12)
        self.assertEqual(len(state.blocks[0].preview_lines), 5)
        self.assertEqual(state.blocks[1].tool_name, "read")
        self.assertEqual(state.blocks[1].total_items, 0)
        self.assertEqual(state.assistant_text, "Found the files.")
        self.assertTrue(state.has_collapsed_blocks)


class EmptyToolCallsTests(unittest.TestCase):
    def test_no_tool_calls(self) -> None:
        result = {"assistant": {"text": "Hello!", "tool_calls": []}}
        state = build_collapsed_state(result)
        self.assertEqual(len(state.blocks), 0)
        self.assertFalse(state.has_collapsed_blocks)
        self.assertEqual(state.assistant_text, "Hello!")

    def test_missing_tool_calls_key(self) -> None:
        result = {"assistant": {"text": "Hello!"}}
        state = build_collapsed_state(result)
        self.assertEqual(len(state.blocks), 0)


class RenderCollapsedOutputTests(unittest.TestCase):
    def test_render_to_buffer(self) -> None:
        result = {
            "assistant": {
                "text": "Done.",
                "tool_calls": [
                    {
                        "tool_call_id": "c1",
                        "tool_name": "glob",
                        "status": "executed",
                        "output": {"files": [f"f{i}.py" for i in range(8)]},
                        "risk_class": "low",
                        "duration_ms": 10,
                    },
                ],
            }
        }
        state = build_collapsed_state(result)
        buf = io.StringIO()
        render_collapsed(state, file=buf)
        output = buf.getvalue()
        self.assertIn("glob", output)
        self.assertIn("8 file(s)", output)
        self.assertIn("+3 more", output)
        self.assertIn("sigil> Done.", output)

    def test_render_no_tools(self) -> None:
        state = CollapsedTurnState(blocks=[], assistant_text="Just text.")
        buf = io.StringIO()
        render_collapsed(state, file=buf)
        output = buf.getvalue()
        self.assertIn("sigil> Just text.", output)
        self.assertNotIn("[", output.split("sigil>")[0])


if __name__ == "__main__":
    unittest.main()
