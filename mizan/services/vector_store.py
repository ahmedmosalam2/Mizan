"""
Real Vector Store & Semantic Search Service for Mizan.

Performs semantic vector retrieval over the 5,000+ SKU Ramadan product catalog.
Supports:
    - OpenAI embeddings (`text-embedding-3-small` / `text-embedding-ada-002`)
    - Fallback TF-IDF + Cosine Similarity semantic index (zero-dependency, robust)
    - Full Arabic & English multilingual retrieval
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


class VectorStore:
    """Multilingual Semantic Search & Retrieval Vector Store."""

    def __init__(self, openai_client: Optional[Any] = None, embedding_model: str = "text-embedding-3-small"):
        self.client = openai_client
        self.embedding_model = embedding_model
        self.documents: List[Dict[str, Any]] = []
        self.doc_vectors: List[List[float]] = []
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}

    def index_products(self, products: List[Dict[str, Any]]) -> None:
        """Index product catalog for semantic search."""
        self.documents = products
        corpus_texts = []
        for p in products:
            # Combined multilingual text representation
            text = (
                f"{p.get('name_en', '')} | {p.get('name_ar', '')} | "
                f"Category: {p.get('category', '')} | "
                f"Price SAR: {p.get('ramadan_price_sar', '')} | Price EGP: {p.get('ramadan_price_egp', '')} | "
                f"{p.get('description_en', '')} | {p.get('description_ar', '')}"
            )
            corpus_texts.append(text)

        # If OpenAI client is configured and API key is present
        if self.client and os.environ.get("OPENAI_API_KEY"):
            try:
                resp = self.client.embeddings.create(input=corpus_texts, model=self.embedding_model)
                self.doc_vectors = [d.embedding for d in resp.data]
                return
            except Exception:
                pass  # Fallback to local vector indexing

        # Local TF-IDF Vector Space Index
        self._build_local_index(corpus_texts)

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [t for t in cleaned.split() if len(t) > 1]

    def _build_local_index(self, corpus: List[str]) -> None:
        tokenized_docs = [self._tokenize(doc) for doc in corpus]
        doc_count = len(tokenized_docs)
        if doc_count == 0:
            return

        # Vocab & Doc Frequencies
        df: Dict[str, int] = Counter()
        for doc in tokenized_docs:
            for term in set(doc):
                df[term] += 1

        self._vocabulary = {term: idx for idx, term in enumerate(df.keys())}
        self._idf = {term: math.log((doc_count + 1) / (count + 1)) + 1.0 for term, count in df.items()}

        # Compute TF-IDF vectors
        self.doc_vectors = []
        for doc in tokenized_docs:
            vec = self._vectorize_tokens(doc)
            self.doc_vectors.append(vec)

    def _vectorize_tokens(self, tokens: List[str]) -> List[float]:
        tf = Counter(tokens)
        vec = [0.0] * len(self._vocabulary)
        norm_sq = 0.0

        for term, count in tf.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                weight = (count / len(tokens)) * self._idf[term]
                vec[idx] = weight
                norm_sq += weight * weight

        norm = math.sqrt(norm_sq)
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if len(vec_a) != len(vec_b):
            return 0.0
        return sum(a * b for a, b in zip(vec_a, vec_b))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search products using semantic similarity."""
        if not self.documents:
            return []

        # If using OpenAI embeddings
        if self.client and os.environ.get("OPENAI_API_KEY") and len(self.doc_vectors) > 0 and len(self.doc_vectors[0]) > len(self._vocabulary):
            try:
                resp = self.client.embeddings.create(input=[query], model=self.embedding_model)
                q_vec = resp.data[0].embedding
                scores: List[Tuple[float, Dict[str, Any]]] = []
                for doc, d_vec in zip(self.documents, self.doc_vectors):
                    sim = self._cosine_similarity(q_vec, d_vec)
                    scores.append((sim, doc))
                scores.sort(key=lambda x: x[0], reverse=True)
                return [d for _, d in scores[:top_k]]
            except Exception:
                pass

        # Fallback Local TF-IDF search
        q_tokens = self._tokenize(query)
        q_vec = self._vectorize_tokens(q_tokens)

        scores = []
        for doc, d_vec in zip(self.documents, self.doc_vectors):
            sim = self._cosine_similarity(q_vec, d_vec)
            scores.append((sim, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scores[:top_k]]
