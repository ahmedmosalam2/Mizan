"""Business-layer models for the executable Ramadan retail scenario."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from mizan.core.contracts import ApprovalStatus, CampaignStatus, StrictModel


class CampaignBrief(StrictModel):
    """Input supplied by a company to create one Ramadan retail campaign."""

    company_id: str = Field(min_length=1, max_length=128)
    campaign_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    product_query: str = Field(min_length=1, max_length=500)
    target_market: Literal["KSA", "EG"]
    target_customer_ids: list[str] = Field(min_length=1, max_length=50)
    requested_channels: list[Literal["meta_ads", "google_ads", "snapchat", "whatsapp", "sms"]] = Field(
        min_length=1
    )
    market_budget: float = Field(gt=0)
    proposed_reallocation_ratio: float = Field(default=0, ge=0, le=1)
    analytics_input: dict[str, float] = Field(default_factory=dict)


class DeploymentEvidence(StrictModel):
    channel: str
    status: str
    attempt: int = Field(ge=1)
    fallback_from: str | None = None
    execution_mode: Literal["sandbox"] = "sandbox"


class CampaignExecution(StrictModel):
    """Sanitized observable outcome of one AUT workflow invocation."""

    campaign_id: str
    company_id: str
    status: CampaignStatus
    approval_id: UUID | None = None
    approval_status: ApprovalStatus | None = None
    selected_product_sku: str | None = None
    compliant_customer_count: int = Field(default=0, ge=0)
    blocked_customer_count: int = Field(default=0, ge=0)
    deployments: list[DeploymentEvidence] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
