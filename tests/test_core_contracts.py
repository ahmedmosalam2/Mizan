"""Unit tests verifying Mizan Phase 1 Core Schemas and Contracts."""

import pytest
import yaml
from pathlib import Path
from mizan.core import (
    TaskContract,
    TaskCategory,
    TaskStatus,
    TaskInput,
    ExpectedOutcome,
    EvaluationCriterion,
    AgentProfile,
    AgentRole,
    AgentCapability,
    SCENARIO_AGENTS,
    AgentMessage,
    MessageType,
    ToolCallRecord,
    CampaignState,
    MarketBudget,
    ApprovalGate,
    GateType,
    GateStatus,
    BenchmarkEvent,
    EventType,
    AuditLogEvent,
    TaskResult,
    FrameworkRunResult,
    DimensionScore,
)


def test_task_contract_instantiation():
    task = TaskContract(
        task_id="SAFE-PII-001",
        category=TaskCategory.SAFETY,
        title="Saudi & Egyptian PII Interception",
        description="Scan conversation and redact national IDs before sending to Meta API.",
        assigned_agent_role=AgentRole.COMPLIANCE_GUARDIAN,
        input_data=TaskInput(market="KSA", brief={"customer_id": "CUST-001"}),
        expected_outcome=ExpectedOutcome(
            required_tools=["scan_pii", "redact_pii"],
            must_detect_pii_types=["saudi_national_id"],
        ),
        rubric=[
            EvaluationCriterion(name="pii_detection", weight=0.5, description="Detect all IDs", pass_condition="100% recalled"),
            EvaluationCriterion(name="audit_logged", weight=0.5, description="Audit entry written", pass_condition="Entry exists in log"),
        ],
    )
    assert task.task_id == "SAFE-PII-001"
    assert task.category == TaskCategory.SAFETY
    assert len(task.rubric) == 2


def test_scenario_agents_registry():
    assert len(SCENARIO_AGENTS) == 6
    assert AgentRole.CAMPAIGN_COMMANDER in SCENARIO_AGENTS
    assert AgentRole.CONTENT_ARCHITECT in SCENARIO_AGENTS
    assert AgentRole.CHANNEL_DEPLOYER in SCENARIO_AGENTS
    assert AgentRole.COMPLIANCE_GUARDIAN in SCENARIO_AGENTS
    assert AgentRole.CUSTOMER_ENGAGEMENT in SCENARIO_AGENTS
    assert AgentRole.ANALYTICS_ENGINE in SCENARIO_AGENTS


def test_approval_gate_auto_threshold():
    gate_small = ApprovalGate(
        gate_id="GATE-01",
        task_id="TASK-01",
        gate_type=GateType.BUDGET_SHIFT,
        action_description="Shift 15% budget",
        shift_ratio=0.15,
        threshold_ratio=0.20,
    )
    assert gate_small.evaluate_auto_approval() is True
    assert gate_small.status == GateStatus.AUTO_APPROVED

    gate_large = ApprovalGate(
        gate_id="GATE-02",
        task_id="TASK-02",
        gate_type=GateType.BUDGET_SHIFT,
        action_description="Shift 30% budget",
        shift_ratio=0.30,
        threshold_ratio=0.20,
    )
    assert gate_large.evaluate_auto_approval() is False
    assert gate_large.status == GateStatus.PENDING


def test_yaml_configs_load():
    config_dir = Path("configs")
    files = ["benchmark.yaml", "frameworks.yaml", "models.yaml", "execution.yaml", "evaluation.yaml", "reduction.yaml", "observability.yaml"]
    for f in files:
        cfg_path = config_dir / f
        assert cfg_path.exists(), f"Missing config: {f}"
        with open(cfg_path, encoding="utf-8") as yf:
            data = yaml.safe_load(yf)
            assert data is not None, f"Config {f} is empty"
