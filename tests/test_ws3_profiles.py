from __future__ import annotations

import unittest

from bomba_sr.governance.tool_profiles import resolve_alias


class ToolAliasResolutionTests(unittest.TestCase):
    def test_alias_resolution(self) -> None:
        self.assertEqual(resolve_alias("read_file"), "read")
        self.assertEqual(resolve_alias("exec_command"), "exec")
        self.assertEqual(resolve_alias("sessions_spawn"), "sessions_spawn")


if __name__ == "__main__":
    unittest.main()
