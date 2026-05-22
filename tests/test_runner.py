"""
Tests for the benchmark runner — orchestration logic, adapter loading, scenario routing.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from benchmarks.runner import _load_adapter, _build_agent_specs, BenchmarkRunner
from benchmarks.adapters.base_adapter import AgentSpec
from benchmarks.scenarios.test_data import AGENT_SPECS, FRAMEWORKS_REGISTRY


class TestAdapterLoading:
    def test_build_agent_specs(self):
        specs = _build_agent_specs()
        assert len(specs) == 6
        assert all(isinstance(s, AgentSpec) for s in specs)
        assert specs[0].name == "CampaignCommander"
        assert specs[0].can_delegate is True

    def test_load_adapter_invalid_returns_none(self):
        adapter = _load_adapter("nonexistent_framework_xyz")
        assert adapter is None

    def test_frameworks_registry_has_20(self):
        assert len(FRAMEWORKS_REGISTRY) == 20

    def test_all_registry_entries_have_required_fields(self):
        for fw in FRAMEWORKS_REGISTRY:
            assert "id" in fw
            assert "name" in fw
            assert "category" in fw


class TestBenchmarkRunner:
    def test_runner_initialization(self):
        runner = BenchmarkRunner()
        assert runner.llm_config["provider"] == "groq"
        assert runner.scorer is not None
        assert runner.all_results == {}
        assert runner.all_scores == []

    def test_runner_custom_config(self):
        config = {"provider": "openai", "model": "gpt-4", "api_key": "test"}
        runner = BenchmarkRunner(llm_config=config)
        assert runner.llm_config["provider"] == "openai"
        assert runner.llm_config["model"] == "gpt-4"
