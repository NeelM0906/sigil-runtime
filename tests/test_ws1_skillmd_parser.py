from __future__ import annotations

import unittest

from bomba_sr.skills.skillmd_parser import SkillMdParser


class SkillMdParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SkillMdParser()

    def test_parse_valid_agentskills_frontmatter(self) -> None:
        content = """---
name: summarize
description: Summarize project state
user-invocable: true
disable-model-invocation: false
risk-level: medium
intent-tags:
  - summary
tools-required:
  - read
metadata: '{"sigil":{"always":true,"requires":{"bins":["python3"],"env":["OPENAI_API_KEY"]}}}'
---
Summarize current workspace status and active priorities.
"""
        descriptor = self.parser.parse_string(content, skill_id="summarize")
        self.assertEqual(descriptor.skill_id, "summarize")
        self.assertEqual(descriptor.name, "summarize")
        self.assertEqual(descriptor.description, "Summarize project state")
        self.assertEqual(descriptor.risk_level, "medium")
        self.assertEqual(descriptor.intent_tags, ("summary",))
        self.assertEqual(descriptor.tools_required, ("read",))
        self.assertTrue(descriptor.eligibility.always)
        self.assertEqual(descriptor.eligibility.required_bins, ("python3",))
        self.assertEqual(descriptor.eligibility.required_env, ("OPENAI_API_KEY",))
        self.assertIn("Summarize current workspace status", descriptor.body_text)

    def test_parse_requires_name_and_description(self) -> None:
        content = """---
name: only-name
---
Body
"""
        with self.assertRaises(ValueError):
            self.parser.parse_string(content, skill_id="only-name")

    def test_parse_openclaw_metadata_overlay(self) -> None:
        content = """---
name: search
description: Search project files
metadata: '{"openclaw":{"requires":{"bins":["rg"],"env":["SERENA_BASE_URL"]},"os":["darwin"]}}'
---
Use rg and serena when available.
"""
        descriptor = self.parser.parse_string(content, skill_id="search")
        self.assertEqual(descriptor.eligibility.required_bins, ("rg",))
        self.assertEqual(descriptor.eligibility.required_env, ("SERENA_BASE_URL",))
        self.assertEqual(descriptor.eligibility.os_filter, ("darwin",))


if __name__ == "__main__":
    unittest.main()
