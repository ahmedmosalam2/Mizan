from abc import ABC, abstractmethod
from typing import List, Optional
from core.domain.entities.campaign import Campaign


class CampaignRepositoryPort(ABC):
    
    @abstractmethod
    async def get_by_id(self, campaign_id: str) -> Optional[Campaign]:

        pass
    
    @abstractmethod
    async def save(self, campaign: Campaign) -> Campaign:

        pass
    
    @abstractmethod
    async def update(self, campaign_id: str, campaign: Campaign) -> Campaign:

        pass
    
    @abstractmethod
    async def delete(self, campaign_id: str) -> bool:

        pass
    
    @abstractmethod
    async def list_all(self) -> List[Campaign]:

        pass