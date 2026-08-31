"""Tests for the framework-neutral AUT and benchmark contracts."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from mizan.core.contracts import (
    ApprovalDecision,
    ApprovalStatus,
    AtomicTask,
    CampaignStateMachine,
    CampaignStatus,
    ErrorCode,
    ErrorRecord,
    EvaluationMetric,
    ExecutionMode,
    TaskInput,
    ToolResponse,
)
from mizan.core.state import CampaignState, MarketBudget
from mizan.core.configuration import RuntimeConfiguration


def test_atomic_task_requires_versioned_evaluation_contract() -> None:
    task = AtomicTask(
        task_id="RAG-PROD-001",
        version="1.0.0",
        objective="Retrieve the product matching a scoped catalog query.",
        input=TaskInput(payload={"query": "air fryer"}, market="KSA", fixture_id="catalog-v1"),
        allowed_tools={"product_search"},
        forbidden_behavior=["cross-company retrieval"],
        success_criteria=["Returns the expected scoped SKU"],
        evaluation_metrics=[EvaluationMetric(name="top_1_accuracy", value=1.0, unit="ratio")],
        difficulty=0.4,
        deterministic_fixture_id="catalog-v1",
    )

    assert task.task_id == "RAG-PROD-001"
    assert task.input.market == "KSA"


def test_failed_tool_response_requires_classified_error() -> None:
    with pytest.raises(ValidationError, match="classified error"):
        ToolResponse(request_id=uuid4(), success=False, duration_ms=5)

    response = ToolResponse(
        request_id=uuid4(),
        success=False,
        duration_ms=5,
        error=ErrorRecord(code=ErrorCode.RATE_LIMIT, message="Retry later", retryable=True),
    )
    assert response.error is not None
    assert response.error.retryable is True


def test_approval_decision_requires_human_identity() -> None:
    with pytest.raises(ValidationError, match="requires an approver"):
        ApprovalDecision(approval_id=uuid4(), status=ApprovalStatus.APPROVED)

    decision = ApprovalDecision(
        approval_id=uuid4(),
        status=ApprovalStatus.REJECTED,
        approved_by="user-finance-1",
        reason="Budget adjustment needs a revised forecast.",
    )
    assert decision.status is ApprovalStatus.REJECTED


def test_campaign_state_machine_enforces_legal_transitions() -> None:
    state = CampaignState(
        campaign_id="campaign-1",
        company_id="company-1",
        campaign_name="Ramadan retail launch",
        markets={
            "KSA": MarketBudget(
                market="KSA",
                currency="SAR",
                allocated_amount=50_000,
                channel_allocations={"meta": 30_000, "snapchat": 20_000},
            )
        },
    )

    transition = state.transition(
        CampaignStatus.PLANNING,
        changed_by="commander-1",
        reason="Campaign brief accepted.",
    )

    assert transition.previous is CampaignStatus.DRAFT
    assert state.status is CampaignStatus.PLANNING
    assert not CampaignStateMachine.can_transition(CampaignStatus.DRAFT, CampaignStatus.DEPLOYED)
    with pytest.raises(ValueError, match="Illegal campaign state transition"):
        state.transition(
            CampaignStatus.DEPLOYED,
            changed_by="commander-1",
            reason="Attempted deployment without compliance.",
        )


def test_contracts_reject_undeclared_boundary_data() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TaskInput(payload={}, market="KSA", unexpected="not allowed")  # type: ignore[call-arg]

    with pytest.raises(ValidationError, match="cannot exceed"):
        MarketBudget(market="EG", currency="EGP", allocated_amount=100, spent_amount=101)

    with pytest.raises(ValidationError, match="must use SAR"):
        MarketBudget(market="KSA", currency="EGP", allocated_amount=100)


def test_execution_mode_is_explicit() -> None:
    assert ExecutionMode.SANDBOX.value == "sandbox"

    with pytest.raises(ValidationError, match="only in real mode"):
        RuntimeConfiguration(
            execution_mode=ExecutionMode.SANDBOX,
            allow_external_channel_dispatch=True,
        )
