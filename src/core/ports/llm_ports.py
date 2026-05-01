from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class LLMPort(ABC):

    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:

        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
   
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
 
        pass
    