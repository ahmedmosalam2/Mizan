from typing import List, Dict
from pydantic import BaseModel, Field

class BaseCompany(BaseModel):
    
    company_name: str = Field(..., description="name)")
    markets: List[str] = Field(..., description="markets")
    brand_guidelines: str = Field(..., description="brand_guidelines")

    def get_supported_payment_methods(self, market: str) -> List[str]:
        
        raise NotImplementedError("This method should be implemented by the child class")
