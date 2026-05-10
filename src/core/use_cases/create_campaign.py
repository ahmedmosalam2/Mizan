from core.domain.entities.campaign import Campaign
from core.ports.Campaign_Repository_Port import CampaignRepositoryPort
from core.ports.llm_ports import LLMPort
from core.ports.vector_db_port import VectorDBPort


class CreateCampaignUseCase:
    
    
    def __init__(self, 
                 campaign_repo: CampaignRepositoryPort,
                 llm_port: LLMPort,
                 vector_db_port: VectorDBPort):

        self.campaign_repo = campaign_repo
        self.llm_port = llm_port
        self.vector_db_port = vector_db_port
    
    async def execute(self, campaign: Campaign) -> Campaign:

        saved_campaign = await self.campaign_repo.save(campaign)

        campaign_description = f"{saved_campaign.name} - {saved_campaign.market}"
        embedding = await self.llm_port.embed(campaign_description)
        

        await self.vector_db_port.store_embedding(
            entity_id=saved_campaign.id,
            entity_type="campaign",
            text=campaign_description,
            embedding=embedding
        )
        
 
        return saved_campaign