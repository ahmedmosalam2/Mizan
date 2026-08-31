from typing import Any, Dict, List, Optional
from story.vectordb.providers.base_provider import BaseVectorDBProvider


class MockVectorDBProvider(BaseVectorDBProvider):
    """
    Mock Vector Database Provider for offline testing.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.storage = []

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        if not ids:
            ids = [f"mock_id_{len(self.storage) + i}" for i in range(len(texts))]
        if not metadatas:
            metadatas = [None] * len(texts)

        for text, meta, text_id in zip(texts, metadatas, ids):
            self.storage.append({
                "id": text_id,
                "document": text,
                "metadata": meta,
                "distance": 0.0
            })

    def query(self, query_text: str, limit: int = 3, **kwargs) -> List[Dict[str, Any]]:
        # Simply return the first N elements from mock storage (pretending they are similar)
        return self.storage[:limit]

    def reset(self) -> None:
        self.storage = []
