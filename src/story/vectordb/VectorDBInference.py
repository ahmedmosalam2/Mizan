from typing import Any, Dict, List, Optional
from story.vectordb.VectorDBProviderFactory import VectorDBProviderFactory


class VectorDBInference:
    """
    High-level entry point for vector database operations in the story layer.
    """

    def __init__(self, provider: str, **kwargs):
        self.config = {
            "provider": provider,
            **kwargs
        }
        self.provider_client = VectorDBProviderFactory.create(self.config)

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add texts to the database."""
        self.provider_client.add_texts(texts, metadatas, ids)

    def query(self, query_text: str, limit: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Search similar texts."""
        return self.provider_client.query(query_text, limit, **kwargs)

    def reset(self) -> None:
        """Clear database collection."""
        self.provider_client.reset()
