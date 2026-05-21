"""
Pydantic schemas for API request/response validation.

Separate from domain entities to keep the API contract independent.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# Campaign Schemas
# ═══════════════════════════════════════════════════════════════════

class CampaignCreateRequest(BaseModel):
    """Request body for creating a new campaign."""
    name: str = Field(..., min_length=1, max_length=255, examples=["حملة رمضان 2026"])
    market: str = Field(..., pattern="^(KSA|EG)$", examples=["KSA"])
    total_budget: float = Field(..., gt=0, examples=[50000.0])
    currency: str = Field(default="SAR", pattern="^(SAR|EGP)$")
    channels: List[str] = Field(..., min_length=1, examples=[["meta", "snapchat", "whatsapp"]])
    target_audiences: List[str] = Field(default_factory=list, examples=[["شباب 18-35"]])
    languages: List[str] = Field(default=["ar", "en"])
    total_spend: float = Field(default=0.0, ge=0)


class CampaignUpdateRequest(BaseModel):
    """Request body for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    market: Optional[str] = Field(None, pattern="^(KSA|EG)$")
    status: Optional[str] = Field(None, pattern="^(planning|active|inactive|draft|paused|completed)$")
    total_budget: Optional[float] = Field(None, gt=0)
    total_spend: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern="^(SAR|EGP)$")
    channels: Optional[List[str]] = None
    target_audiences: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    channel_allocations: Optional[Dict[str, float]] = None


class CampaignResponse(BaseModel):
    """Single campaign response."""
    id: str
    name: str
    market: str
    status: str
    total_spend: float
    total_budget: float
    currency: str
    channel_allocations: Dict[str, float] = {}
    channels: List[str] = []
    target_audiences: List[str] = []
    languages: List[str] = []
    metrics: Dict[str, Any] = {}
    consent_verified: bool = False
    pii_alerts_count: int = 0
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""
    campaigns: List[CampaignResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════
# Agent / Execution Schemas
# ═══════════════════════════════════════════════════════════════════

class AgentInfo(BaseModel):
    """Information about an available agent."""
    name: str
    description: str
    type: str


class OptimizeCampaignRequest(BaseModel):
    """Request to run agent optimization on a campaign."""
    agents: List[str] = Field(
        default=["CampaignCommander", "ContentArchitect", "ChannelDeployer", "AnalyticsAgent", "BudgetOptimizer"],
        description="Which agents to run",
    )
    parallel: bool = Field(default=False, description="Run agents in parallel")


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""
    id: str
    campaign_id: str
    agent_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════
# Brief Schema
# ═══════════════════════════════════════════════════════════════════

class CampaignBriefRequest(BaseModel):
    """Request to submit a campaign brief for commander agent."""
    name: str
    market: str = "KSA"
    total_budget: float
    currency: str = "SAR"
    channels: List[str]
    target_audience: str
    start_date: datetime
    end_date: datetime
    objectives: List[str] = Field(default_factory=list)
    language: str = "ar"
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Generic Responses
# ═══════════════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    database: str = "connected"
    timestamp: datetime = Field(default_factory=datetime.now)
