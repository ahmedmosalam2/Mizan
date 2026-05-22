"""
Shared pytest fixtures for Mizan benchmark tests.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List

import pytest

# Ensure src/ is on the path for imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from benchmarks.adapters.base_adapter import (
    AgentSpec,
    BaseFrameworkAdapter,
    ScenarioResult,
    TokenUsage,
    ToolSpec,
    TraceEntry,
)
from benchmarks.scoring.scorer import BenchmarkScorer, DimensionScore, FrameworkScore
from benchmarks.scenarios.test_data import (
    AGENT_SPECS,
    APPROVAL_RULES,
    BUDGET_REALLOCATION_REQUEST,
    CAMPAIGN_BRIEF,
    CONTENT_GENERATION_TASK,
    CONVERSATION_HISTORY,
    DEPLOYMENT_TASK,
    EXPECTED_PII_DETECTIONS,
    EXPECTED_RECALL,
    FRAMEWORKS_REGISTRY,
    MEMORY_FOLLOW_UP,
    MULTIMODAL_TASK,
    PII_TEST_TEXTS,
    PRODUCT_CATALOG,
    SIMULATED_APPROVALS,
)
from benchmarks.mocks.mock_llm import MockLLMClient, get_mock_response, MOCK_RESPONSES


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def scorer():
    """Fresh BenchmarkScorer instance."""
    return BenchmarkScorer()


@pytest.fixture
def mock_llm():
    """MockLLMClient for deterministic LLM responses."""
    return MockLLMClient(default_latency_ms=10)  # Fast for tests


@pytest.fixture
def sample_agent_specs() -> List[AgentSpec]:
    """Build AgentSpec objects from the test data."""
    return [
        AgentSpec(
            name=spec["name"],
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            can_delegate=spec.get("can_delegate", False),
        )
        for spec in AGENT_SPECS
    ]


@pytest.fixture
def completed_scenario_result() -> ScenarioResult:
    """A completed ScenarioResult with realistic data for testing."""
    return ScenarioResult(
        scenario_id="campaign_planning",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["campaign_planning"],
        total_duration_ms=1500.0,
        token_usage=TokenUsage(
            prompt_tokens=200,
            completion_tokens=500,
            total_tokens=700,
            estimated_cost_usd=0.0042,
            model_name="test-model",
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="CampaignCommander",
                action="task_decomposition",
                output_summary="Decomposed into 4 sub-tasks",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:01",
                agent_name="ContentArchitect",
                action="content_generation",
                output_summary="Generated 12 ad variants",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:02",
                agent_name="ComplianceGuardian",
                action="compliance_check",
                output_summary="PDPL check passed",
            ),
        ],
        agent_count=6,
        tool_calls=3,
        used_parallel=True,
        used_branching=True,
        used_retry=True,
    )


@pytest.fixture
def failed_scenario_result() -> ScenarioResult:
    """A failed ScenarioResult for edge-case testing."""
    return ScenarioResult(
        scenario_id="campaign_planning",
        framework_name="test_framework",
        status="failed",
        error="Connection timeout",
        total_duration_ms=5000.0,
        token_usage=TokenUsage(),
    )


@pytest.fixture
def pii_scenario_result() -> ScenarioResult:
    """A completed PII scan result with detected PII."""
    import json

    output = json.loads(MOCK_RESPONSES["pii_scan"])
    return ScenarioResult(
        scenario_id="pii_scan",
        framework_name="test_framework",
        status="completed",
        output=output,
        total_duration_ms=800.0,
        token_usage=TokenUsage(
            prompt_tokens=150,
            completion_tokens=300,
            total_tokens=450,
            estimated_cost_usd=0.003,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="ComplianceGuardian",
                action="pii_scan",
                output_summary="Detected 7 PII items",
            ),
        ],
        agent_count=1,
        pii_detected=True,
        pii_redacted=True,
    )


@pytest.fixture
def memory_scenario_result() -> ScenarioResult:
    """A completed cross-session memory result."""
    return ScenarioResult(
        scenario_id="cross_session_chat",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["cross_session_memory"],
        total_duration_ms=600.0,
        token_usage=TokenUsage(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            estimated_cost_usd=0.002,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="CustomerEngagement",
                action="memory_recall",
            ),
        ],
        agent_count=1,
        used_memory=True,
    )


@pytest.fixture
def hitl_scenario_result() -> ScenarioResult:
    """A completed HITL budget approval result."""
    return ScenarioResult(
        scenario_id="budget_approval",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["budget_approval"],
        total_duration_ms=700.0,
        token_usage=TokenUsage(
            prompt_tokens=120,
            completion_tokens=250,
            total_tokens=370,
            estimated_cost_usd=0.0025,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="AnalyticsAgent",
                action="budget_analysis",
            ),
        ],
        agent_count=2,
        used_approval_gate=True,
    )


@pytest.fixture
def observability_scenario_result() -> ScenarioResult:
    """A completed observability/deployment result."""
    return ScenarioResult(
        scenario_id="channel_deploy",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["channel_deploy"],
        total_duration_ms=2000.0,
        token_usage=TokenUsage(
            prompt_tokens=100,
            completion_tokens=300,
            total_tokens=400,
            estimated_cost_usd=0.003,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="ChannelDeployer",
                action="deploy_meta_ads",
                output_summary="Success",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:01",
                agent_name="ChannelDeployer",
                action="deploy_snapchat",
                output_summary="Rate limited — retry",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:02",
                agent_name="ChannelDeployer",
                action="deploy_snapchat_retry",
                output_summary="Success after retry",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:03",
                agent_name="ChannelDeployer",
                action="deploy_google_ads",
                output_summary="Success",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:04",
                agent_name="ChannelDeployer",
                action="deploy_whatsapp_fallback_sms",
                output_summary="WhatsApp rejected → SMS fallback",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:05",
                agent_name="ChannelDeployer",
                action="deploy_email",
                output_summary="Success",
            ),
        ],
        agent_count=1,
        used_retry=True,
    )


@pytest.fixture
def multimodal_scenario_result() -> ScenarioResult:
    """A completed multimodal ad result."""
    return ScenarioResult(
        scenario_id="multimodal_ad",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["multimodal_ad"],
        total_duration_ms=900.0,
        token_usage=TokenUsage(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            estimated_cost_usd=0.002,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="ContentArchitect",
                action="multimodal_generation",
            ),
        ],
        agent_count=1,
    )


@pytest.fixture
def tool_use_scenario_result() -> ScenarioResult:
    """A completed tool use / content generation result."""
    return ScenarioResult(
        scenario_id="content_generation",
        framework_name="test_framework",
        status="completed",
        output=MOCK_RESPONSES["content_generation"],
        total_duration_ms=1200.0,
        token_usage=TokenUsage(
            prompt_tokens=150,
            completion_tokens=400,
            total_tokens=550,
            estimated_cost_usd=0.0035,
        ),
        trace=[
            TraceEntry(
                timestamp="2026-01-01T00:00:00",
                agent_name="ContentArchitect",
                action="tool_call_search_catalog",
                output_summary="Found 3 products",
            ),
            TraceEntry(
                timestamp="2026-01-01T00:00:01",
                agent_name="ContentArchitect",
                action="tool_call_generate_content",
                output_summary="4 ad variants generated",
            ),
        ],
        agent_count=1,
        tool_calls=5,
    )


@pytest.fixture
def all_scenario_results(
    completed_scenario_result,
    tool_use_scenario_result,
    pii_scenario_result,
    hitl_scenario_result,
    memory_scenario_result,
    observability_scenario_result,
    multimodal_scenario_result,
) -> Dict[str, ScenarioResult]:
    """All 7 scenario results keyed by scenario_id."""
    return {
        "campaign_planning": completed_scenario_result,
        "content_generation": tool_use_scenario_result,
        "pii_scan": pii_scenario_result,
        "budget_approval": hitl_scenario_result,
        "cross_session_chat": memory_scenario_result,
        "channel_deploy": observability_scenario_result,
        "multimodal_ad": multimodal_scenario_result,
    }
