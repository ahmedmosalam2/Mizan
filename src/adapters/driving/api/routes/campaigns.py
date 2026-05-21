"""
Campaign CRUD + optimization routes.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from adapters.driving.api.dependencies import (
    get_campaign_repo,
    get_llm,
    get_approval_port,
)
from adapters.driving.api.schemas import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignResponse,
    CampaignListResponse,
    CampaignBriefRequest,
    MessageResponse,
)
from core.domain.entities.campaign import Campaign, CampaignStatus
from core.ports.Campaign_Repository_Port import CampaignRepositoryPort
from core.ports.llm_ports import LLMPort
from core.ports.human_approval_port import HumanApprovalPort

router = APIRouter(prefix="/api/v1/campaigns", tags=["Campaigns"])


# ── Helpers ────────────────────────────────────────────────────────
def _entity_to_response(campaign: Campaign) -> CampaignResponse:
    """Convert domain entity to API response."""
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        market=campaign.market if isinstance(campaign.market, str) else campaign.market.value,
        status=campaign.status if isinstance(campaign.status, str) else campaign.status.value,
        total_spend=campaign.total_spend,
        total_budget=campaign.total_budget,
        currency=campaign.currency,
        channel_allocations=campaign.channel_allocations,
        channels=[c if isinstance(c, str) else c.value for c in campaign.channels],
        target_audiences=campaign.target_audiences,
        languages=campaign.languages,
        metrics={},
        consent_verified=campaign.consent_verified,
        pii_alerts_count=campaign.pii_alerts_count,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════
# CRUD Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign",
)
async def create_campaign(
    body: CampaignCreateRequest,
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
):
    """Create a new marketing campaign."""
    campaign = Campaign(
        id=str(uuid.uuid4()),
        name=body.name,
        market=body.market,
        total_budget=body.total_budget,
        total_spend=body.total_spend,
        currency=body.currency,
        channels=body.channels,
        target_audiences=body.target_audiences,
        languages=body.languages,
    )
    saved = await repo.save(campaign)
    return _entity_to_response(saved)


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List all campaigns",
)
async def list_campaigns(
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
):
    """Retrieve all campaigns."""
    campaigns = await repo.list_all()
    return CampaignListResponse(
        campaigns=[_entity_to_response(c) for c in campaigns],
        total=len(campaigns),
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign by ID",
)
async def get_campaign(
    campaign_id: str,
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
):
    """Retrieve a specific campaign by its ID."""
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    return _entity_to_response(campaign)


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign",
)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdateRequest,
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
):
    """Update an existing campaign."""
    existing = await repo.get_by_id(campaign_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    # Apply only the fields that were provided
    update_data = body.model_dump(exclude_unset=True)
    campaign_data = existing.model_dump()
    campaign_data.update(update_data)
    updated_campaign = Campaign(**campaign_data)

    saved = await repo.update(campaign_id, updated_campaign)
    return _entity_to_response(saved)


@router.delete(
    "/{campaign_id}",
    response_model=MessageResponse,
    summary="Delete a campaign",
)
async def delete_campaign(
    campaign_id: str,
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
):
    """Delete a campaign by its ID."""
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    return MessageResponse(message="Campaign deleted successfully")


# ═══════════════════════════════════════════════════════════════════
# Agent / Optimization Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/{campaign_id}/optimize",
    summary="Run AI agents on a campaign",
)
async def optimize_campaign(
    campaign_id: str,
    repo: CampaignRepositoryPort = Depends(get_campaign_repo),
    llm: LLMPort = Depends(get_llm),
    approval: HumanApprovalPort = Depends(get_approval_port),
):
    """
    Run the full agent orchestration pipeline on a campaign.

    This executes: CampaignCommander → ContentArchitect → ChannelDeployer
                   → BudgetOptimizer → AnalyticsAgent
    """
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    # Import agents
    from core.domain.agents.campaign_commander import CampaignCommanderAgent
    from core.domain.agents.content_architect import ContentArchitectAgent
    from core.domain.agents.channel_deployer import ChannelDeployerAgent
    from core.domain.agents.analytics_agent import AnalyticsAgent
    from core.domain.agents.budget_optimizer_agent import BudgetOptimizerAgent
    from core.domain.agents.orchestrator import SerialAgentOrchestrator
    from core.domain.agents.agent_context import AgentContext
    from core.domain.entities.agent_helper import Task
    from datetime import datetime

    # Build agent pipeline
    agents = [
        CampaignCommanderAgent(llm=llm, approval_port=approval),
        ContentArchitectAgent(llm=llm),
        ChannelDeployerAgent(llm=llm),
        BudgetOptimizerAgent(llm=llm),
        AnalyticsAgent(llm=llm),
    ]

    # Build brief from campaign data
    brief_data = {
        "name": campaign.name,
        "market": campaign.market if isinstance(campaign.market, str) else campaign.market.value,
        "total_budget": campaign.total_budget,
        "currency": campaign.currency,
        "channels": [c if isinstance(c, str) else c.value for c in campaign.channels],
        "target_audience": ", ".join(campaign.target_audiences) if campaign.target_audiences else "General",
        "start_date": datetime.now().isoformat(),
        "end_date": datetime.now().isoformat(),
        "objectives": ["Brand Awareness", "Conversions"],
        "language": campaign.languages[0] if campaign.languages else "ar",
    }

    task = Task(
        id=f"optimize_{campaign_id}",
        goal=f"Optimize campaign: {campaign.name}",
        context={"brief": brief_data},
    )

    context = AgentContext(
        workflow_id=f"wf_{campaign_id}",
        task_id=task.id,
    )

    orchestrator = SerialAgentOrchestrator(max_retries=2, debug=True)

    try:
        result = await orchestrator.orchestrate(agents, task, context)
        return {
            "campaign_id": campaign_id,
            "status": result.status if hasattr(result, "status") else "completed",
            "execution_log": orchestrator.get_execution_log(),
            "result": result.model_dump() if hasattr(result, "model_dump") else str(result),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}",
        )
