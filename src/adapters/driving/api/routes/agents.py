"""
Agent information and execution history routes.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.driving.api.dependencies import get_db
from adapters.driving.api.schemas import AgentInfo, AgentExecutionResponse
from db.models import AgentExecutionModel

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


# ── Available Agents ───────────────────────────────────────────────
AVAILABLE_AGENTS = [
    AgentInfo(
        name="CampaignCommander",
        description="Decomposes campaign briefs into actionable sub-tasks for other agents",
        type="orchestration",
    ),
    AgentInfo(
        name="ContentArchitect",
        description="Generates campaign content and creative copy",
        type="content",
    ),
    AgentInfo(
        name="ChannelDeployer",
        description="Creates deployment plans for ad channels (Meta, Snapchat, etc.)",
        type="deployment",
    ),
    AgentInfo(
        name="BudgetOptimizer",
        description="Optimizes budget allocation across channels",
        type="optimization",
    ),
    AgentInfo(
        name="AnalyticsAgent",
        description="Analyzes campaign performance and provides insights",
        type="analytics",
    ),
]


@router.get(
    "",
    response_model=List[AgentInfo],
    summary="List available agents",
)
async def list_agents():
    """Get all available AI agents and their descriptions."""
    return AVAILABLE_AGENTS


@router.get(
    "/executions/{campaign_id}",
    response_model=List[AgentExecutionResponse],
    summary="Get agent executions for a campaign",
)
async def get_campaign_executions(
    campaign_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all agent execution records for a specific campaign."""
    result = await session.execute(
        select(AgentExecutionModel)
        .where(AgentExecutionModel.campaign_id == campaign_id)
        .order_by(AgentExecutionModel.created_at.desc())
    )
    executions = result.scalars().all()

    return [
        AgentExecutionResponse(
            id=ex.id,
            campaign_id=ex.campaign_id,
            agent_name=ex.agent_name,
            status=ex.status,
            result=ex.result,
            error=ex.error,
            execution_time_ms=ex.execution_time_ms,
            created_at=ex.created_at,
        )
        for ex in executions
    ]
