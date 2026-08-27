"""Embedding provider interface.

The rest of the system depends only on this Protocol, never on Gemini
directly, so the provider can be swapped (or faked in tests) without touching
retrieval, chunking or the API. Embedding is a distinct responsibility from
both the vector store and the LLM; keeping them behind separate interfaces is
the point.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

TaskType = Literal["document", "query"]


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    @property
    def recommended_threshold(self) -> float:
        """Cosine relevance below which a chunk is not trustworthy evidence.

        Provider-specific because embedding models differ in how they scale
        cosine similarity for related-but-not-identical text.
        """
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed corpus chunks for storage."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single user query for search."""
        ...
