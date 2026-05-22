"""
Tests for rubric weight validation — ensuring rubric integrity.
"""

import pytest
from benchmarks.scoring.rubrics import RUBRICS, get_dimension_weights


class TestRubricWeights:
    """Rubric sub-criteria weights must sum to exactly 1.0 per dimension."""

    @pytest.mark.parametrize("dimension", list(RUBRICS.keys()))
    def test_sub_criteria_weights_sum_to_one(self, dimension):
        sub = RUBRICS[dimension]["sub_criteria"]
        total = sum(c["weight"] for c in sub.values())
        assert abs(total - 1.0) < 1e-9, (
            f"{dimension}: sub-criteria weights sum to {total}, expected 1.0"
        )

    def test_dimension_weights_sum_to_one(self):
        weights = get_dimension_weights()
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"Dimension weights sum to {total}"

    def test_all_seven_dimensions_present(self):
        expected = {"orchestration", "tool_use", "safety", "human_in_the_loop",
                    "memory", "observability", "multimodal"}
        assert set(RUBRICS.keys()) == expected

    @pytest.mark.parametrize("dimension", list(RUBRICS.keys()))
    def test_all_sub_criteria_have_levels(self, dimension):
        for name, criteria in RUBRICS[dimension]["sub_criteria"].items():
            assert "levels" in criteria, f"{dimension}.{name} missing levels"
            assert len(criteria["levels"]) >= 2, f"{dimension}.{name} needs >=2 levels"
            assert 10 in criteria["levels"], f"{dimension}.{name} missing level 10"
            assert 0 in criteria["levels"], f"{dimension}.{name} missing level 0"
