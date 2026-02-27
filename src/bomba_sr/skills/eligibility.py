from __future__ import annotations

import os
import shutil
import sys
from typing import Mapping

from bomba_sr.skills.descriptor import SkillDescriptor


class EligibilityEngine:
    def check(self, skill: SkillDescriptor, env: Mapping[str, str] | None = None) -> bool:
        rules = skill.eligibility
        if rules.always:
            return True

        env_map = env or os.environ
        if not self._check_os(rules.os_filter):
            return False
        if not self._check_bins(rules.required_bins, require_all=True):
            return False
        if not self._check_bins(rules.any_bins, require_all=False):
            return False
        if not self._check_env(rules.required_env, env_map):
            return False
        return True

    @staticmethod
    def _check_os(os_filter: tuple[str, ...]) -> bool:
        if not os_filter:
            return True
        current = sys.platform.lower()
        normalized = [x.lower() for x in os_filter]
        if current.startswith("darwin"):
            return "darwin" in normalized
        if current.startswith("linux"):
            return "linux" in normalized
        if current.startswith("win"):
            return "win32" in normalized or "windows" in normalized
        return current in normalized

    @staticmethod
    def _check_bins(bins: tuple[str, ...], require_all: bool) -> bool:
        if not bins:
            return True
        checks = [shutil.which(name) is not None for name in bins]
        return all(checks) if require_all else any(checks)

    @staticmethod
    def _check_env(keys: tuple[str, ...], env: Mapping[str, str]) -> bool:
        if not keys:
            return True
        for key in keys:
            if key in env and str(env[key]).strip():
                continue
            return False
        return True
