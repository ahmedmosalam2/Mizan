from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class VectorDBPort(ABC):
    """Port for Vector Database operations (embeddings storage and similarity search)."""

    @abstractmethod
    async def store_embedding(self, 
                            entity_id: str, 
                            entity_type: str,
                            text: str, 
                            embedding: list[float]) -> bool:
        """
        Store an embedding in the Vector DB.
        
        Args:
            entity_id: Entity identifier (campaign_id, task_id)
            entity_type: Entity type ("campaign", "task", "content")
            text: Original text
            embedding: The vector
            
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    async def search_similar(self, 
                            embedding: list[float], 
                            entity_type: str,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings.
        
        Args:
            embedding: The query embedding
            entity_type: Entity type to search within
            limit: Number of results
            
        Returns:
            List of results (entity_id, score, text)
        """
        pass
    
    @abstractmethod
    async def delete_embedding(self, entity_id: str) -> bool:
        """
        Delete an embedding.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def get_embedding(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a stored embedding.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            The data (embedding, text, metadata)
        """
        pass
