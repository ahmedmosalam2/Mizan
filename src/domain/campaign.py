"""
Domain models for Ramadan e-commerce campaigns.

These are the core business objects that agents work with:
- Campaign: An overall marketing campaign (with budget, dates, objectives)
- Product: A product being promoted (with multilingual descriptions)
- Channel: A marketing channel (Meta, Google, WhatsApp, etc.)
- CampaignState: The current state of a campaign (budget spent, impressions, etc.)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class Channel(Enum):
    """Supported marketing channels."""
    META_FACEBOOK = "meta_facebook"
    META_INSTAGRAM = "meta_instagram"
    GOOGLE_SEARCH = "google_search"
    GOOGLE_SHOPPING = "google_shopping"
    SNAPCHAT = "snapchat"
    TIKTOK = "tiktok"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


class Country(Enum):
    """Market regions."""
    SAUDI_ARABIA = "KSA"
    EGYPT = "EG"
    UAE = "AE"
    KUWAIT = "KW"
    BAHRAIN = "BH"


class Currency(Enum):
    """Supported currencies."""
    SAR = "SAR"  # Saudi Riyal
    EGP = "EGP"  # Egyptian Pound
    AED = "AED"  # UAE Dirham


@dataclass
class Product:
    """
    A product being promoted in the campaign.
    
    Must support multilingual content (Arabic + English).
    """
    product_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Multilingual names
    name_ar: str = ""
    name_en: str = ""
    
    # Multilingual descriptions
    description_ar: str = ""
    description_en: str = ""
    
    # Category for targeting
    category: str = ""
    
    # Pricing by market
    price_sar: float = 0.0  # Price in Saudi Riyal
    price_egp: float = 0.0  # Price in Egyptian Pound
    price_aed: float = 0.0  # Price in UAE Dirham
    
    # Media
    image_url: str = ""
    video_url: Optional[str] = None
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_name(self, language: str = "ar") -> str:
        """Get product name in specified language."""
        return self.name_ar if language == "ar" else self.name_en
    
    def get_description(self, language: str = "ar") -> str:
        """Get product description in specified language."""
        return self.description_ar if language == "ar" else self.description_en
    
    def get_price(self, country: Country) -> float:
        """Get product price for a specific country."""
        if country == Country.SAUDI_ARABIA:
            return self.price_sar
        elif country == Country.EGYPT:
            return self.price_egp
        elif country == Country.UAE:
            return self.price_aed
        return 0.0
    
    def __str__(self) -> str:
        return f"Product({self.name_ar}/{self.name_en}, SAR {self.price_sar})"


@dataclass
class ChannelBudget:
    """Budget allocation for a specific channel."""
    channel: Channel
    budget_usd: float
    daily_limit_usd: Optional[float] = None
    spent_usd: float = 0.0
    
    def remaining_budget(self) -> float:
        """Calculate remaining budget."""
        return self.budget_usd - self.spent_usd
    
    def budget_utilization_percent(self) -> float:
        """Calculate budget utilization percentage."""
        if self.budget_usd == 0:
            return 0.0
        return (self.spent_usd / self.budget_usd) * 100


@dataclass
class CampaignMetrics:
    """Performance metrics for a campaign."""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue_usd: float = 0.0
    spend_usd: float = 0.0
    
    def ctr(self) -> float:
        """Click-through rate."""
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0
    
    def conversion_rate(self) -> float:
        """Conversion rate."""
        return (self.conversions / self.clicks * 100) if self.clicks > 0 else 0.0
    
    def roas(self) -> float:
        """Return on Ad Spend."""
        return (self.revenue_usd / self.spend_usd) if self.spend_usd > 0 else 0.0
    
    def cpc(self) -> float:
        """Cost per click."""
        return (self.spend_usd / self.clicks) if self.clicks > 0 else 0.0
    
    def cpa(self) -> float:
        """Cost per acquisition."""
        return (self.spend_usd / self.conversions) if self.conversions > 0 else 0.0


@dataclass
class Campaign:
    """
    A marketing campaign targeting one or more MENA markets.
    
    Attributes:
        campaign_id: Unique campaign identifier
        name: Campaign name (e.g., "Ramadan 2026 Flash Sale")
        company_name: Company running the campaign
        description: Campaign description
        start_date: Campaign start date
        end_date: Campaign end date
        products: List of products being promoted
        target_countries: List of countries to target
        channels: Budget allocation by channel
        objectives: Campaign objectives (e.g., "Drive sales", "Build awareness")
        metrics: Performance metrics by channel
    """
    
    campaign_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    company_name: str = ""
    description: str = ""
    
    # Timeline
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    
    # Products
    products: List[Product] = field(default_factory=list)
    
    # Markets
    target_countries: List[Country] = field(default_factory=list)
    
    # Budget
    channel_budgets: List[ChannelBudget] = field(default_factory=list)
    total_budget_usd: float = 0.0
    
    # Objectives
    objectives: List[str] = field(default_factory=list)
    
    # Metrics
    metrics: Dict[Channel, CampaignMetrics] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    
    def total_spent(self) -> float:
        """Calculate total budget spent across all channels."""
        return sum(budget.spent_usd for budget in self.channel_budgets)
    
    def total_remaining(self) -> float:
        """Calculate total remaining budget."""
        return sum(budget.remaining_budget() for budget in self.channel_budgets)
    
    def get_channel_budget(self, channel: Channel) -> Optional[ChannelBudget]:
        """Get budget for a specific channel."""
        for budget in self.channel_budgets:
            if budget.channel == channel:
                return budget
        return None
    
    def add_channel_budget(self, channel: Channel, budget_usd: float) -> None:
        """Add budget for a channel."""
        existing = self.get_channel_budget(channel)
        if existing:
            existing.budget_usd = budget_usd
        else:
            self.channel_budgets.append(
                ChannelBudget(channel=channel, budget_usd=budget_usd)
            )
    
    def add_product(self, product: Product) -> None:
        """Add a product to the campaign."""
        if product not in self.products:
            self.products.append(product)
    
    def overall_roas(self) -> float:
        """Calculate overall ROAS across all channels."""
        total_revenue = sum(m.revenue_usd for m in self.metrics.values())
        total_spend = sum(m.spend_usd for m in self.metrics.values())
        return (total_revenue / total_spend) if total_spend > 0 else 0.0
    
    def overall_metrics(self) -> CampaignMetrics:
        """Get aggregated metrics across all channels."""
        result = CampaignMetrics()
        for metrics in self.metrics.values():
            result.impressions += metrics.impressions
            result.clicks += metrics.clicks
            result.conversions += metrics.conversions
            result.revenue_usd += metrics.revenue_usd
            result.spend_usd += metrics.spend_usd
        return result
    
    def __str__(self) -> str:
        countries = ", ".join(c.value for c in self.target_countries)
        return (
            f"Campaign({self.name}, {countries}, "
            f"Budget: ${self.total_budget_usd}, "
            f"Products: {len(self.products)})"
        )


@dataclass
class CampaignConfig:
    """
    Configuration for creating a campaign from YAML/JSON.
    
    This mirrors the structure in campaign_config.yaml
    """
    name: str
    company_name: str
    start_date: str  # ISO format
    end_date: str    # ISO format
    products: List[Dict[str, Any]]  # Raw product data
    channels: List[Dict[str, Any]]  # Raw channel data
    markets: List[Dict[str, Any]]   # Raw market data
    objectives: List[str]
    special_notes: Optional[str] = None
    
    def to_campaign(self, created_by: str = "system") -> Campaign:
        """Convert this config to a Campaign object."""
        campaign = Campaign(
            name=self.name,
            company_name=self.company_name,
            start_date=datetime.fromisoformat(self.start_date),
            end_date=datetime.fromisoformat(self.end_date),
            objectives=self.objectives,
            created_by=created_by,
        )
        
        # Add products
        for product_data in self.products:
            product = Product(
                name_ar=product_data.get("name_ar", ""),
                name_en=product_data.get("name_en", ""),
                description_ar=product_data.get("description_ar", ""),
                description_en=product_data.get("description_en", ""),
                price_sar=product_data.get("price_sar", 0.0),
                price_egp=product_data.get("price_egp", 0.0),
                image_url=product_data.get("image_url", ""),
            )
            campaign.add_product(product)
        
        # Add channel budgets
        for channel_data in self.channels:
            channel_name = channel_data.get("name", "").upper().replace(" ", "_")
            try:
                channel = Channel[channel_name]
                budget_usd = channel_data.get("budget_usd", 0.0)
                campaign.add_channel_budget(channel, budget_usd)
            except KeyError:
                # Skip unknown channels
                pass
        
        return campaign
