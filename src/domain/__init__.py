"""
Domain package - Core business models for e-commerce campaigns.
"""

from .campaign import (
    Product,
    Campaign,
    Channel,
    Country,
    Currency,
    ChannelBudget,
    CampaignMetrics,
    CampaignConfig,
)

__all__ = [
    "Product",
    "Campaign",
    "Channel",
    "Country",
    "Currency",
    "ChannelBudget",
    "CampaignMetrics",
    "CampaignConfig",
]
