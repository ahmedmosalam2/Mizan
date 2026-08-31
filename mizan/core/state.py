"""
Core State Models for Mizan.

Defines the shared state, market budget allocations, and session memory context.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MarketBudget(BaseModel):
    """Budget and spend tracker for a target jurisdiction."""
    market: str  # 'KSA' or 'EG'
    currency: str  # 'SAR' or 'EGP'
    allocated_amount: float
    spent_amount: float = 0.0
    channel_allocations: Dict[str, float] = Field(default_factory=dict)


class CampaignState(BaseModel):
    """Global shared campaign state across all 6 agents."""
    campaign_id: str
    campaign_name: str
    phase: str
    markets: Dict[str, MarketBudget] = Field(default_factory=dict)
    active_tasks: List[str] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    deployed_channels: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    pending_approvals: List[str] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
