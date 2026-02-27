from __future__ import annotations

import unittest

from bomba_sr.commands.disclosure import SkillDisclosure
from bomba_sr.skills.descriptor import SkillDescriptor, SkillEligibility


def _skill(skill_id: str, name: str, disable_model_invocation: bool = False) -> SkillDescriptor:
    return SkillDescriptor(
        skill_id=skill_id,
        version="1.0.0",
        name=name,
        description=f"Description for {name}",
        source="filesystem",
        source_path=f"/tmp/{skill_id}/SKILL.md",
        body_text="Body",
        intent_tags=(),
        tools_required=(),
        risk_level="low",
        default_enabled=True,
        user_invocable=True,
        disable_model_invocation=disable_model_invocation,
        command_dispatch=None,
        command_tool=None,
        command_arg_mode="raw",
        eligibility=SkillEligibility(),
        metadata={},
        _body_loaded=True,
    )


class SkillDisclosureTests(unittest.TestCase):
    def test_format_skill_index_xml_and_token_estimate(self) -> None:
        disclosure = SkillDisclosure()
        skills = {
            "a": _skill("a", "alpha"),
            "b": _skill("b", "beta", disable_model_invocation=True),
            "c": _skill("c", "charlie"),
        }
        xml = disclosure.format_skill_index_xml(skills)
        self.assertIn('<available_skills count="2">', xml)
        self.assertIn('id="a"', xml)
        self.assertIn('id="c"', xml)
        self.assertNotIn('id="b"', xml)
        self.assertGreater(disclosure.estimate_index_tokens(skills), 15)

    def test_format_skill_body_context(self) -> None:
        disclosure = SkillDisclosure()
        skill = _skill("review", "review")
        body = "Use strict review format."
        formatted = disclosure.format_skill_body_context(skill, body)
        self.assertIn("<selected_skill", formatted)
        self.assertIn("Use strict review format.", formatted)


if __name__ == "__main__":
    unittest.main()
