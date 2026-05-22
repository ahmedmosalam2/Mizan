"""
Tests for the scoring engine — verifies score calculations produce
correct, consistent results across all 7 dimensions.
"""

from copy import deepcopy
import pytest

from benchmarks.scoring.scorer import BenchmarkScorer, FrameworkScore
from benchmarks.adapters.base_adapter import ScenarioResult, TokenUsage, TraceEntry
from benchmarks.mocks.mock_llm import MOCK_RESPONSES


class TestScorerOrchestration:
    def test_perfect_orchestration(self, scorer, completed_scenario_result):
        scores, _ = scorer._score_orchestration(
            completed_scenario_result, scorer.rubrics["orchestration"]["sub_criteria"])
        assert scores["multi_agent_creation"] == 10
        assert scores["parallel_execution"] == 10
        assert scores["conditional_branching"] == 10

    def test_failed_orchestration_zeros(self, scorer, failed_scenario_result):
        scores, notes = scorer._score_orchestration(
            failed_scenario_result, scorer.rubrics["orchestration"]["sub_criteria"])
        assert all(s == 0 for s in scores.values())

    def test_partial_agent_count(self, scorer, completed_scenario_result):
        r = deepcopy(completed_scenario_result)
        r.agent_count = 4
        scores, _ = scorer._score_orchestration(r, scorer.rubrics["orchestration"]["sub_criteria"])
        assert scores["multi_agent_creation"] == 7
        r.agent_count = 1
        scores, _ = scorer._score_orchestration(r, scorer.rubrics["orchestration"]["sub_criteria"])
        assert scores["multi_agent_creation"] == 0


class TestScorerSafety:
    def test_perfect_pii(self, scorer, pii_scenario_result):
        scores, _ = scorer._score_safety(
            pii_scenario_result, scorer.rubrics["safety"]["sub_criteria"])
        assert scores["saudi_id_detection"] == 10.0
        assert scores["egyptian_id_detection"] == 10.0
        assert scores["pii_redaction"] == 10

    def test_failed_safety_zeros(self, scorer, failed_scenario_result):
        scores, notes = scorer._score_safety(
            failed_scenario_result, scorer.rubrics["safety"]["sub_criteria"])
        assert all(s == 0 for s in scores.values())


class TestScorerMemory:
    def test_full_recall(self, scorer, memory_scenario_result):
        scores, _ = scorer._score_memory(
            memory_scenario_result, scorer.rubrics["memory"]["sub_criteria"])
        assert scores["cross_session_recall"] == 10.0
        assert scores["shared_state"] == 10

    def test_partial_recall(self, scorer):
        r = ScenarioResult(scenario_id="cross_session_chat", framework_name="t",
                           status="completed", output="قلاية فيلبس", token_usage=TokenUsage(), used_memory=True)
        scores, _ = scorer._score_memory(r, scorer.rubrics["memory"]["sub_criteria"])
        assert 0 < scores["cross_session_recall"] < 10


class TestScorerHITL:
    def test_with_approval(self, scorer, hitl_scenario_result):
        scores, _ = scorer._score_hitl(
            hitl_scenario_result, scorer.rubrics["human_in_the_loop"]["sub_criteria"])
        assert scores["pause_resume"] == 10
        assert scores["conditional_gates"] == 10


class TestScorerObservability:
    def test_rich_trace(self, scorer, observability_scenario_result):
        scores, _ = scorer._score_observability(
            observability_scenario_result, scorer.rubrics["observability"]["sub_criteria"])
        assert scores["execution_trace"] == 10
        assert scores["error_handling"] == 10


class TestFrameworkScoring:
    def test_all_scenarios(self, scorer, all_scenario_results):
        fw = scorer.score_framework("test_fw", all_scenario_results)
        assert len(fw.dimensions) == 7
        assert 0 < fw.total_score <= 10.0
        assert fw.total_tokens > 0

    def test_consistency(self, scorer, all_scenario_results):
        s1 = scorer.score_framework("a", all_scenario_results)
        s2 = scorer.score_framework("b", all_scenario_results)
        assert s1.total_score == s2.total_score

    def test_missing_scenarios_zero(self, scorer):
        partial = {"campaign_planning": ScenarioResult(
            scenario_id="campaign_planning", framework_name="t", status="completed",
            output=MOCK_RESPONSES["campaign_planning"], token_usage=TokenUsage(total_tokens=100),
            trace=[TraceEntry(agent_name="C", action="p")], agent_count=6)}
        fw = scorer.score_framework("partial", partial)
        assert fw.dimensions["orchestration"].score > 0
        assert fw.dimensions["tool_use"].score == 0

    def test_all_failed_zero(self, scorer):
        failed = {sid: ScenarioResult(scenario_id=sid, framework_name="f", status="failed",
                                      error="crash", token_usage=TokenUsage())
                  for sid in ["campaign_planning", "content_generation", "pii_scan",
                              "budget_approval", "cross_session_chat", "channel_deploy", "multimodal_ad"]}
        assert scorer.score_framework("f", failed).total_score == 0.0


class TestComparison:
    def test_ranking(self, scorer, all_scenario_results):
        s1 = scorer.score_framework("strong", all_scenario_results)
        s2 = scorer.score_framework("weak", {"campaign_planning": all_scenario_results["campaign_planning"]})
        cmp = scorer.compare_frameworks([s1, s2])
        assert cmp["ranking"][0]["framework"] == "strong"
        assert cmp["frameworks_count"] == 2
