"""
FastAPI dependency injection.

Provides database sessions, repositories, and use cases to route handlers.
"""
import os
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session
from adapters.driven.repositories.pg_campaign_repository import PgCampaignRepository
from adapters.driven.llm.groq_adapter import GroqAdapter
from adapters.driven.approval.auto_approve_adapter import AutoApproveAdapter
from core.ports.Campaign_Repository_Port import CampaignRepositoryPort
from core.ports.llm_ports import LLMPort
from core.ports.human_approval_port import HumanApprovalPort
from helper.config import Config


# ── Database Session ───────────────────────────────────────────────
async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    """Provide an async database session."""
    return session


# ── Repositories ───────────────────────────────────────────────────
async def get_campaign_repo(
    session: AsyncSession = Depends(get_db),
) -> CampaignRepositoryPort:
    """Provide a campaign repository backed by PostgreSQL."""
    return PgCampaignRepository(session)


# ── LLM Provider ──────────────────────────────────────────────────
def get_llm() -> LLMPort:
    """Provide the configured LLM adapter."""
    api_key = Config.GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return GroqAdapter(api_key=api_key)


# ── Human Approval ─────────────────────────────────────────────────
def get_approval_port() -> HumanApprovalPort:
    """Provide the human approval adapter (auto-approve for now)."""
    return AutoApproveAdapter()
