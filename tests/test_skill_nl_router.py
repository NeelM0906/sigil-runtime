from __future__ import annotations

import unittest

from bomba_sr.commands.skill_nl_router import parse_skill_nl_intent


class SkillNlRouterTests(unittest.TestCase):
    def test_catalog_intent(self) -> None:
        intent = parse_skill_nl_intent("list skills from clawhub")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.name, "catalog_list")
        self.assertEqual(intent.source, "clawhub")

    def test_install_request_intent(self) -> None:
        intent = parse_skill_nl_intent("please install skill daily-brief from clawhub")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.name, "install_request")
        self.assertEqual(intent.source, "clawhub")
        self.assertEqual(intent.skill_id, "daily-brief")

    def test_trust_set_intent(self) -> None:
        intent = parse_skill_nl_intent("set trust for clawhub to blocked")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.name, "trust_set")
        self.assertEqual(intent.trust_mode, "blocked")

    def test_install_apply_intent(self) -> None:
        req_id = "123e4567-e89b-12d3-a456-426614174000"
        intent = parse_skill_nl_intent(f"apply install request {req_id}")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.name, "install_apply")
        self.assertEqual(intent.request_id, req_id)

    def test_missing_install_args_returns_none(self) -> None:
        intent = parse_skill_nl_intent("install from clawhub")
        self.assertIsNone(intent)


if __name__ == "__main__":
    unittest.main()
