from enum import Enum
from typing import Optional, Dict, List, Any
from src.core.domain.entities.base import BaseEntity
from pydantic import BaseModel,Field
from datetime import datetime


class Market(str, Enum):
    SAUDI_ARABIA = "KSA"
    EGYPT = "EG"

    

class CampaignStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"



class Channel(str, Enum):
    META = "meta"
    GOOGLE = "google"
    SNAPCHAT = "snapchat"
    TIKTOK = "tiktok"
    WHATSAPP = "whatsapp"
    SMS = "sms"
class CampaignMetrics(BaseModel):
    roas: float = 0.0
    cpa: float = 0.0
    ctr: float = 0.0
    spend: float = 0.0
    conversions: int = 0


class Campaign(BaseModel):
    id: str
    name: str
    market: Market
    status: CampaignStatus = CampaignStatus.PLANNING
    total_spend: float
    total_budget: float
    currency: str  # SAR or EGP
    channel_allocations: Dict[Channel, float] = Field(default_factory=dict)
    
    channels: List[Channel]
    target_audiences: List[str] = Field(default_factory=list)
    languages: List[str] = ["ar", "en"]
    metrics: Dict[Channel, CampaignMetrics] = Field(default_factory=dict)
    
   
    consent_verified: bool = False
    pii_alerts_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    class Config:
        use_enum_values = True