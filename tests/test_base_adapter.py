"""
Tests for the BaseFrameworkAdapter contract — verifies all utility methods
and ensures the abstract interface is correctly defined.
"""

import pytest
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ScenarioResult, TokenUsage,
    TraceEntry, ToolSpec, ScenarioType,
)


class TestBaseAdapterContract:
    """Verify the abstract base class structure."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseFrameworkAdapter(framework_name="test")

    def test_has_seven_abstract_methods(self):
        abstract_methods = BaseFrameworkAdapter.__abstractmethods__
        expected = {"setup", "teardown", "run_orchestration", "run_with_tools",
                    "run_safety_check", "run_with_approval", "run_with_memory",
                    "run_with_tracing", "run_multimodal"}
        assert expected == abstract_methods

    def test_scenario_types_match_dimensions(self):
        expected = {"orchestration", "tool_use", "safety", "human_in_the_loop",
                    "memory", "observability", "multimodal"}
        actual = {t.value for t in ScenarioType}
        assert expected == actual


class TestTokenUsage:
    def test_default_values(self):
        t = TokenUsage()
        assert t.total_tokens == 0
        assert t.estimated_cost_usd == 0.0

    def test_custom_values(self):
        t = TokenUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300,
                       estimated_cost_usd=0.005, model_name="test")
        assert t.total_tokens == 300


class TestTraceEntry:
    def test_default_trace(self):
        t = TraceEntry()
        assert t.agent_name == ""
        assert t.error is None


class TestAgentSpec:
    def test_agent_spec_fields(self):
        a = AgentSpec(name="Test", role="Tester", goal="Test things",
                      backstory="A test agent")
        assert a.name == "Test"
        assert a.can_delegate is False
        assert a.memory is True
        assert a.tools == []


class TestToolSpec:
    def test_tool_spec(self):
        def fn(x): return x
        t = ToolSpec(name="test_tool", description="A tool", function=fn)
        assert t.name == "test_tool"
        assert callable(t.function)


class TestScenarioResult:
    def test_default_result(self):
        r = ScenarioResult(scenario_id="test", framework_name="fw")
        assert r.status == "not_started"
        assert r.output is None
        assert r.agent_count == 0

    def test_behavior_flags(self):
        r = ScenarioResult(scenario_id="t", framework_name="f",
                           used_parallel=True, used_retry=True, pii_detected=True)
        assert r.used_parallel is True
        assert r.used_retry is True
        assert r.pii_detected is True
