"""End-to-end integration tests for Mizan Benchmark runner and scoring."""

import pytest
from mizan.runner.run import run_framework
from mizan.runner.matrix import run_matrix
from mizan.scenario.loader import build_scenario
from mizan.scoring.evaluator import BenchmarkEvaluator


@pytest.mark.asyncio
async def test_scenario_builder():
    scenario = build_scenario()
    assert len(scenario.products) >= 5
    assert len(scenario.customers) >= 5
    assert len(scenario.channels) >= 5
    assert "orchestration" in scenario.probes_to_run


@pytest.mark.asyncio
async def test_native_adapter_run(tmp_path):
    report = await run_framework(framework_name="native", results_dir=str(tmp_path))
    assert report.total_score >= 8.0
    assert report.probes_completed >= 5
    assert "orchestration" in report.dimension_scores
    assert report.dimension_scores["orchestration"].score >= 8.0


@pytest.mark.asyncio
async def test_matrix_runner(tmp_path):
    reports = await run_matrix(
        frameworks=["native", "crewai", "langgraph"],
        results_dir=str(tmp_path),
        report_file=str(tmp_path / "LEADERBOARD.md"),
    )
    assert len(reports) == 3
    assert all(r.total_score > 0 for r in reports)
