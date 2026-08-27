"""Retrieval: query embedding -> vector search -> gate/diversify -> context.

This is the RETRIEVE and SELECT half of "retrieve -> select -> generate ->
cite". The relevance gate here is what makes reliable no-answer behaviour
possible: if nothing clears the threshold, the caller never reaches the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider
from app.models.documents import RetrievedChunk
from app.vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    query: str
    # True when at least one chunk cleared the relevance threshold. The
    # generation layer refuses to answer when this is False.
    has_grounding: bool
    top_relevance: float


class Retriever:
    def __init__(
        self, store: ChromaStore, embedder: EmbeddingProvider, settings: Settings
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._settings = settings

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        tag: str | None = None,
    ) -> RetrievalResult:
        top_k = top_k or self._settings.top_k
        threshold = self._effective_threshold(threshold)

        query_vec = self._embedder.embed_query(query)
        # Oversample so the threshold and per-note diversity cap have room to
        # work before we trim to top_k.
        candidates = self._store.query(
            query_vec,
            top_k=top_k * self._settings.candidate_multiplier,
            where={"tags": {"$contains": tag}} if tag else None,
        )

        gated = [c for c in candidates if c.relevance >= threshold]
        selected = self._diversify(gated, top_k)

        top_relevance = candidates[0].relevance if candidates else 0.0
        logger.info(
            "Retrieval: %d candidates, %d above threshold %.2f, %d selected "
            "(top relevance %.3f)",
            len(candidates),
            len(gated),
            threshold,
            len(selected),
            top_relevance,
        )
        return RetrievalResult(
            chunks=selected,
            query=query,
            has_grounding=bool(selected),
            top_relevance=top_relevance,
        )

    def _effective_threshold(self, override: float | None) -> float:
        """Explicit override wins; then configured value; else provider default."""
        if override is not None:
            return override
        if self._settings.relevance_threshold is not None:
            return self._settings.relevance_threshold
        return getattr(self._embedder, "recommended_threshold", 0.55)

    def _diversify(
        self, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Cap chunks per note so one long note cannot dominate the context."""
        cap = self._settings.max_chunks_per_note
        counts: dict[str, int] = {}
        kept: list[RetrievedChunk] = []
        for chunk in chunks:  # already sorted by relevance desc
            note = chunk.rel_path
            if counts.get(note, 0) >= cap:
                continue
            counts[note] = counts.get(note, 0) + 1
            kept.append(chunk)
            if len(kept) >= top_k:
                break
        return kept
