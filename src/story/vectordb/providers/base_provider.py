from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVectorDBProvider(ABC):
    """
    Base class for all vector database providers in the story layer.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = config.get("collection_name", "mizan_default")

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> None:
        """Add texts to the vector database."""
        pass

    @abstractmethod
    def query(self, query_text: str, limit: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Query vector database for similar texts."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Clear collection contents."""
        pass
