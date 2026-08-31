"""Tenant-scoped campaign state built on the canonical state machine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from mizan.core.contracts import (
    CampaignStateMachine,
    CampaignStatus,
    StrictModel,
    utc_now,
)


class MarketBudget(StrictModel):
    """Budget and spend for one market; monetary values are non-negative."""

    market: Literal["KSA", "EG"]
    currency: Literal["SAR", "EGP"]
    allocated_amount: float = Field(ge=0)
    spent_amount: float = Field(default=0, ge=0)
    channel_allocations: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_budget(self) -> "MarketBudget":
        expected_currency = "SAR" if self.market == "KSA" else "EGP"
        if self.currency != expected_currency:
            raise ValueError(f"{self.market} budgets must use {expected_currency}")
        if self.spent_amount > self.allocated_amount:
            raise ValueError("Market spend cannot exceed its allocated budget")
        if any(amount < 0 for amount in self.channel_allocations.values()):
            raise ValueError("Channel allocations cannot be negative")
        if sum(self.channel_allocations.values()) > self.allocated_amount:
            raise ValueError("Channel allocations cannot exceed the market budget")
        return self


class CampaignTransition(StrictModel):
    """Observable transition stored with the campaign trajectory."""

    previous: CampaignStatus
    current: CampaignStatus
    changed_by: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1_000)
    changed_at: datetime = Field(default_factory=utc_now)


class CampaignState(StrictModel):
    """Authoritative campaign state; agents may only request legal transitions."""

    campaign_id: str = Field(min_length=1, max_length=128)
    company_id: str = Field(min_length=1, max_length=128)
    campaign_name: str = Field(min_length=1, max_length=256)
    status: CampaignStatus = CampaignStatus.DRAFT
    markets: dict[Literal["KSA", "EG"], MarketBudget] = Field(default_factory=dict)
    active_tasks: set[str] = Field(default_factory=set)
    completed_tasks: set[str] = Field(default_factory=set)
    deployed_channels: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pending_approvals: set[str] = Field(default_factory=set)
    shared_context: dict[str, Any] = Field(default_factory=dict)
    transition_history: list[CampaignTransition] = Field(default_factory=list)

    def transition(self, target: CampaignStatus, *, changed_by: str, reason: str) -> CampaignTransition:
        """Validate and record a legal transition before mutating state."""
        CampaignStateMachine.require_transition(self.status, target)
        record = CampaignTransition(
            previous=self.status,
            current=target,
            changed_by=changed_by,
            reason=reason,
        )
        self.status = target
        self.transition_history.append(record)
        return record
