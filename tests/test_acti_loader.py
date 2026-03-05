"""Tests for the ACT-I architecture loader."""

from __future__ import annotations

import pytest
from pathlib import Path
from bomba_sr.acti.loader import (
    load_beings,
    load_clusters,
    load_skill_families,
    load_lever_matrix,
    get_sister_profile,
    get_planning_context,
    get_full_architecture,
    get_being_identity_text,
    BEING_SISTER_MAP,
    LEVERS,
    SHARED_HEART_SKILLS,
    _invalidate_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    _invalidate_cache()
    yield
    _invalidate_cache()


ACTI_ROOT = Path(__file__).resolve().parent.parent / "workspaces" / "acti-architecture"
SKIP = not ACTI_ROOT.is_dir()
reason = "acti-architecture not present"


@pytest.mark.skipif(SKIP, reason=reason)
class TestLoadBeings:
    def test_loads_19_beings(self):
        beings = load_beings(ACTI_ROOT)
        assert len(beings) == 19

    def test_each_being_has_required_fields(self):
        for b in load_beings(ACTI_ROOT):
            assert b["id"]
            assert b["name"]
            assert b["sister_id"], f"{b['id']} has no sister_id"

    def test_being_sister_map_covers_all(self):
        beings = load_beings(ACTI_ROOT)
        for b in beings:
            assert b["id"] in BEING_SISTER_MAP, f"{b['id']} missing from BEING_SISTER_MAP"

    def test_analyst_has_clusters(self):
        beings = load_beings(ACTI_ROOT)
        analyst = next(b for b in beings if b["id"] == "the-analyst")
        assert analyst["positions"] == 429
        assert len(analyst["clusters"]) >= 6
        assert analyst["sister_id"] == "scholar"

    def test_shared_heart_skills_on_all(self):
        for b in load_beings(ACTI_ROOT):
            assert len(b["shared_heart_skills"]) == 4


@pytest.mark.skipif(SKIP, reason=reason)
class TestLoadClusters:
    def test_loads_80_clusters(self):
        clusters = load_clusters(ACTI_ROOT)
        assert len(clusters) == 80

    def test_cluster_has_required_fields(self):
        for c in load_clusters(ACTI_ROOT):
            assert c["id"]
            assert c["name"]
            assert c["family"]


@pytest.mark.skipif(SKIP, reason=reason)
class TestLoadSkillFamilies:
    def test_loads_9_families(self):
        families = load_skill_families(ACTI_ROOT)
        assert len(families) == 9

    def test_family_positions_sum(self):
        families = load_skill_families(ACTI_ROOT)
        total = sum(f["positions"] for f in families)
        assert total >= 2524  # families may slightly exceed being-level sum


@pytest.mark.skipif(SKIP, reason=reason)
class TestLeverMatrix:
    def test_matrix_has_entries(self):
        matrix = load_lever_matrix(ACTI_ROOT)
        assert len(matrix) >= 17  # all operational beings

    def test_analyst_full_lever_coverage(self):
        matrix = load_lever_matrix(ACTI_ROOT)
        assert len(matrix["the-analyst"]) == 8


@pytest.mark.skipif(SKIP, reason=reason)
class TestSisterProfile:
    def test_forge_profile(self):
        profile = get_sister_profile("forge", ACTI_ROOT)
        assert len(profile["beings"]) == 9
        assert profile["positions_total"] == 1297
        assert len(profile["clusters"]) > 0
        assert len(profile["shared_heart_skills"]) == 4

    def test_scholar_profile(self):
        profile = get_sister_profile("scholar", ACTI_ROOT)
        assert len(profile["beings"]) == 2
        assert profile["positions_total"] == 455

    def test_recovery_profile(self):
        profile = get_sister_profile("recovery", ACTI_ROOT)
        assert len(profile["beings"]) == 4
        assert profile["positions_total"] == 479

    def test_prime_profile(self):
        profile = get_sister_profile("prime", ACTI_ROOT)
        assert len(profile["beings"]) == 4
        assert profile["positions_total"] == 293

    def test_unknown_sister_empty(self):
        profile = get_sister_profile("nonexistent", ACTI_ROOT)
        assert profile["beings"] == []
        assert profile["positions_total"] == 0


@pytest.mark.skipif(SKIP, reason=reason)
class TestPlanningContext:
    def test_compact_text(self):
        ctx = get_planning_context(ACTI_ROOT)
        assert "ACT-I Architecture Reference" in ctx
        assert "Forge" in ctx
        assert "Scholar" in ctx
        assert len(ctx) < 3000

    def test_mentions_all_sisters(self):
        ctx = get_planning_context(ACTI_ROOT)
        for sid in ("Prime", "Scholar", "Forge", "Recovery"):
            assert sid in ctx


@pytest.mark.skipif(SKIP, reason=reason)
class TestFullArchitecture:
    def test_all_keys_present(self):
        arch = get_full_architecture(ACTI_ROOT)
        assert "beings" in arch
        assert "clusters" in arch
        assert "skill_families" in arch
        assert "levers" in arch
        assert "lever_matrix" in arch
        assert "sister_profiles" in arch
        assert "shared_heart_skills" in arch
        assert "being_sister_map" in arch
        assert "stats" in arch

    def test_stats(self):
        arch = get_full_architecture(ACTI_ROOT)
        assert arch["stats"]["total_beings"] == 19
        assert arch["stats"]["total_clusters"] == 80
        assert arch["stats"]["total_positions"] == 2524
        assert arch["stats"]["total_skill_families"] == 9
        assert arch["stats"]["total_levers"] == 8


@pytest.mark.skipif(SKIP, reason=reason)
class TestGetBeingIdentityText:
    def test_analyst_identity(self):
        text = get_being_identity_text("the-analyst", ACTI_ROOT)
        assert "The Analyst" in text
        assert "Domain:" in text
        assert "Clusters" in text
        assert "Heart Skills:" in text
        assert "Lever Coverage:" in text

    def test_unknown_being_returns_empty(self):
        text = get_being_identity_text("nonexistent", ACTI_ROOT)
        assert text == ""

    def test_apex_beings_also_work(self):
        text = get_being_identity_text("sai-prime", ACTI_ROOT)
        assert "PRIME" in text.upper()


class TestConstants:
    def test_levers(self):
        assert len(LEVERS) == 8

    def test_shared_heart_skills(self):
        assert len(SHARED_HEART_SKILLS) == 4

    def test_being_sister_map(self):
        assert len(BEING_SISTER_MAP) == 19
        assert BEING_SISTER_MAP["the-analyst"] == "scholar"
        assert BEING_SISTER_MAP["the-writer"] == "forge"
        assert BEING_SISTER_MAP["the-connector"] == "recovery"
        assert BEING_SISTER_MAP["sai-prime"] == "prime"
