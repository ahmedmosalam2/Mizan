import os
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings

from story.vectordb.providers.base_provider import BaseVectorDBProvider


class ChromaProvider(BaseVectorDBProvider):
    """
    ChromaDB vector database provider.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.persist_directory = config.get("persist_directory", "./chroma_db")
        
        # Initialize Chromadb client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(allow_reset=True)
        )
        
        self.embedding_function = config.get("embedding_function")
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        if not ids:
            ids = [f"id_{i}" for i in range(len(texts))]
            
        self.collection.upsert(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, limit: int = 3, **kwargs) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=limit,
            **kwargs
        )
        
        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [None] * len(docs)
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
            
            for i in range(len(docs)):
                formatted_results.append({
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metas[i],
                    "distance": distances[i],
                })
                
        return formatted_results

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
