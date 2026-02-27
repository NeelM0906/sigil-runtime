from __future__ import annotations

import unittest

from bomba_sr.governance.tool_profiles import PROFILE_TOOLS, ToolProfile, profile_from_value, resolve_alias


class ToolProfilesTests(unittest.TestCase):
    def test_alias_resolution(self) -> None:
        self.assertEqual(resolve_alias("read_file"), "read")
        self.assertEqual(resolve_alias("exec_command"), "exec")
        self.assertEqual(resolve_alias("sessions_spawn"), "sessions_spawn")

    def test_profile_membership(self) -> None:
        coding = PROFILE_TOOLS[ToolProfile.CODING]
        assert coding is not None
        self.assertIn("read", coding)
        self.assertIn("code_search", coding)
        self.assertIn("sessions_spawn", coding)

        research = PROFILE_TOOLS[ToolProfile.RESEARCH]
        assert research is not None
        self.assertIn("read", research)
        self.assertNotIn("write", research)
        self.assertNotIn("apply_patch", research)

        self.assertIsNone(PROFILE_TOOLS[ToolProfile.FULL])

    def test_profile_from_value(self) -> None:
        self.assertEqual(profile_from_value("coding"), ToolProfile.CODING)
        self.assertEqual(profile_from_value(ToolProfile.RESEARCH), ToolProfile.RESEARCH)
        self.assertEqual(profile_from_value("unknown"), ToolProfile.FULL)


if __name__ == "__main__":
    unittest.main()
