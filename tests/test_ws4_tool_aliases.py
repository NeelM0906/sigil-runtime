from __future__ import annotations

import unittest

from bomba_sr.governance.tool_profiles import resolve_alias


class ToolAliasTests(unittest.TestCase):
    def test_legacy_aliases_resolve_to_canonical(self) -> None:
        self.assertEqual(resolve_alias("read_file"), "read")
        self.assertEqual(resolve_alias("write_file"), "write")
        self.assertEqual(resolve_alias("edit_file"), "edit")
        self.assertEqual(resolve_alias("exec_command"), "exec")
        self.assertEqual(resolve_alias("glob_files"), "glob")
        self.assertEqual(resolve_alias("grep_content"), "grep")
        self.assertEqual(resolve_alias("spawn_subagent"), "sessions_spawn")
        self.assertEqual(resolve_alias("poll_subagent"), "sessions_poll")


if __name__ == "__main__":
    unittest.main()
