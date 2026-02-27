from __future__ import annotations

import sys
import unittest

from bomba_sr.skills.descriptor import SkillDescriptor, SkillEligibility
from bomba_sr.skills.eligibility import EligibilityEngine


def _skill(eligibility: SkillEligibility) -> SkillDescriptor:
    return SkillDescriptor(
        skill_id="demo",
        version="1.0.0",
        name="demo",
        description="demo",
        source="filesystem",
        source_path="/tmp/demo/SKILL.md",
        body_text="demo",
        intent_tags=(),
        tools_required=(),
        risk_level="low",
        default_enabled=True,
        user_invocable=True,
        disable_model_invocation=False,
        command_dispatch=None,
        command_tool=None,
        command_arg_mode="raw",
        eligibility=eligibility,
        metadata={},
        _body_loaded=True,
    )


class EligibilityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EligibilityEngine()

    def test_always_true_bypasses_checks(self) -> None:
        descriptor = _skill(
            SkillEligibility(
                always=True,
                os_filter=("definitely-not-this-os",),
                required_bins=("definitely_missing_bin",),
                required_env=("MISSING_ENV",),
            )
        )
        self.assertTrue(self.engine.check(descriptor, env={}))

    def test_required_env_gate(self) -> None:
        descriptor = _skill(SkillEligibility(required_env=("OPENAI_API_KEY",)))
        self.assertFalse(self.engine.check(descriptor, env={}))
        self.assertTrue(self.engine.check(descriptor, env={"OPENAI_API_KEY": "sk-test"}))

    def test_bin_gates(self) -> None:
        descriptor_required = _skill(SkillEligibility(required_bins=("python3",)))
        self.assertTrue(self.engine.check(descriptor_required, env={}))

        descriptor_any = _skill(SkillEligibility(any_bins=("definitely_missing_bin", "python3")))
        self.assertTrue(self.engine.check(descriptor_any, env={}))

        descriptor_fail = _skill(SkillEligibility(required_bins=("definitely_missing_bin",)))
        self.assertFalse(self.engine.check(descriptor_fail, env={}))

    def test_os_filter(self) -> None:
        current = "darwin" if sys.platform.startswith("darwin") else "linux"
        descriptor_ok = _skill(SkillEligibility(os_filter=(current,)))
        self.assertTrue(self.engine.check(descriptor_ok, env={}))

        descriptor_bad = _skill(SkillEligibility(os_filter=("windows",)))
        if current != "windows":
            self.assertFalse(self.engine.check(descriptor_bad, env={}))


if __name__ == "__main__":
    unittest.main()
