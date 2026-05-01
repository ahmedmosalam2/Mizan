from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class VectorDBPort(ABC):
    """عقد وسيط بين Core Logic والـ Vector Database"""
    
    @abstractmethod
    async def store_embedding(self, 
                            entity_id: str, 
                            entity_type: str,
                            text: str, 
                            embedding: list[float]) -> bool:
        """
        احفظ embedding في الـ Vector DB
        
        Args:
            entity_id: معرّف الـ entity (campaign_id, task_id)
            entity_type: نوع الـ entity ("campaign", "task", "content")
            text: النص الأصلي
            embedding: الـ vector
            
        Returns:
            True إذا نجح الحفظ
        """
        pass
    
    @abstractmethod
    async def search_similar(self, 
                            embedding: list[float], 
                            entity_type: str,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """
        ابحث عن embeddings متشابهة
        
        Args:
            embedding: الـ query embedding
            entity_type: نوع الـ entity للبحث فيه
            limit: عدد النتائج
            
        Returns:
            قائمة بالنتائج (entity_id, score, text)
        """
        pass
    
    @abstractmethod
    async def delete_embedding(self, entity_id: str) -> bool:
        """
        احذف embedding
        
        Args:
            entity_id: معرّف الـ entity
            
        Returns:
            True إذا نجح الحذف
        """
        pass
    
    @abstractmethod
    async def get_embedding(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        جيب embedding محفوظ
        
        Args:
            entity_id: معرّف الـ entity
            
        Returns:
            البيانات (embedding, text, metadata)
        """
        pass