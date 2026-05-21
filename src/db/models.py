"""
SQLAlchemy ORM models for PostgreSQL.

Maps domain entities to database tables.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY

from db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ── Campaign ───────────────────────────────────────────────────────
class CampaignModel(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # KSA / EG
    status: Mapped[str] = mapped_column(String(20), default="planning")
    total_spend: Mapped[float] = mapped_column(Float, default=0.0)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)  # SAR / EGP

    # JSON columns for flexible nested data
    channel_allocations: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    channels: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    target_audiences: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    languages: Mapped[Optional[list]] = mapped_column(JSON, default=lambda: ["ar", "en"])
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    consent_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_alerts_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    executions: Mapped[list["AgentExecutionModel"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Campaign {self.id} - {self.name}>"


# ── Agent Execution ────────────────────────────────────────────────
class AgentExecutionModel(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    campaign_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    campaign: Mapped["CampaignModel"] = relationship(back_populates="executions")

    def __repr__(self):
        return f"<AgentExecution {self.id} - {self.agent_name}>"


# ── Task ───────────────────────────────────────────────────────────
class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    constraints: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<Task {self.id} - {self.goal[:30]}>"
