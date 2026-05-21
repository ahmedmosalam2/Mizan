"""
PostgreSQL implementation of CampaignRepositoryPort.

Uses async SQLAlchemy to interact with the campaigns table.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.entities.campaign import Campaign
from core.ports.Campaign_Repository_Port import CampaignRepositoryPort
from db.models import CampaignModel


class PgCampaignRepository(CampaignRepositoryPort):
    """Async PostgreSQL adapter for campaign persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Helpers ─────────────────────────────────────────────────
    @staticmethod
    def _model_to_entity(model: CampaignModel) -> Campaign:
        """Convert SQLAlchemy model → domain entity."""
        return Campaign(
            id=model.id,
            name=model.name,
            market=model.market,
            status=model.status,
            total_spend=model.total_spend,
            total_budget=model.total_budget,
            currency=model.currency,
            channel_allocations=model.channel_allocations or {},
            channels=model.channels or [],
            target_audiences=model.target_audiences or [],
            languages=model.languages or ["ar", "en"],
            metrics=model.metrics or {},
            consent_verified=model.consent_verified,
            pii_alerts_count=model.pii_alerts_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _entity_to_model(entity: Campaign) -> CampaignModel:
        """Convert domain entity → SQLAlchemy model."""
        return CampaignModel(
            id=entity.id or str(uuid.uuid4()),
            name=entity.name,
            market=entity.market,
            status=entity.status,
            total_spend=entity.total_spend,
            total_budget=entity.total_budget,
            currency=entity.currency,
            channel_allocations=entity.channel_allocations,
            channels=[c if isinstance(c, str) else c.value for c in entity.channels],
            target_audiences=entity.target_audiences,
            languages=entity.languages,
            metrics={k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in entity.metrics.items()},
            consent_verified=entity.consent_verified,
            pii_alerts_count=entity.pii_alerts_count,
        )

    # ── Port implementation ─────────────────────────────────────
    async def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        result = await self.session.execute(
            select(CampaignModel).where(CampaignModel.id == campaign_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def save(self, campaign: Campaign) -> Campaign:
        model = self._entity_to_model(campaign)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._model_to_entity(model)

    async def update(self, campaign_id: str, campaign: Campaign) -> Campaign:
        result = await self.session.execute(
            select(CampaignModel).where(CampaignModel.id == campaign_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Update fields
        model.name = campaign.name
        model.market = campaign.market if isinstance(campaign.market, str) else campaign.market.value
        model.status = campaign.status if isinstance(campaign.status, str) else campaign.status.value
        model.total_spend = campaign.total_spend
        model.total_budget = campaign.total_budget
        model.currency = campaign.currency
        model.channel_allocations = campaign.channel_allocations
        model.channels = [c if isinstance(c, str) else c.value for c in campaign.channels]
        model.target_audiences = campaign.target_audiences
        model.languages = campaign.languages
        model.metrics = {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in campaign.metrics.items()}
        model.consent_verified = campaign.consent_verified
        model.pii_alerts_count = campaign.pii_alerts_count

        await self.session.flush()
        await self.session.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, campaign_id: str) -> bool:
        result = await self.session.execute(
            sa_delete(CampaignModel).where(CampaignModel.id == campaign_id)
        )
        return result.rowcount > 0

    async def list_all(self) -> List[Campaign]:
        result = await self.session.execute(
            select(CampaignModel).order_by(CampaignModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]
