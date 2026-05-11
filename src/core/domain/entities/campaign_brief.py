from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from core.domain.entities.campaign import Market, Channel


class CampaignBrief(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    market: Market
    total_budget: float
    currency: str = "SAR"
    channels: List[str]
    target_audience: str
    start_date: datetime
    end_date: datetime
    objectives: List[str] = Field(default_factory=list)
    language: str = "ar"
    notes: Optional[str] = None
