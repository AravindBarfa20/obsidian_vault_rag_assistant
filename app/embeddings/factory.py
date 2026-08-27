"""Select an embedding provider from configuration.

Falls back to the deterministic FakeEmbedder when no Gemini key is present, so
`/ingest` and `/query` work end-to-end in local dev and CI without credentials.
The active provider is reported by /health so the choice is never silent.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)


def build_embedder(settings: Settings) -> EmbeddingProvider:
    if settings.has_gemini_key:
        from app.embeddings.gemini_embedder import GeminiEmbedder

        logger.info("Using Gemini embedder: %s", settings.embedding_model)
        return GeminiEmbedder(
            api_key=settings.gemini_api_key,
            model_name=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
        )

    from app.embeddings.fake_embedder import FakeEmbedder

    logger.warning(
        "No GEMINI_API_KEY set -> using deterministic FakeEmbedder "
        "(offline mode; not for production retrieval quality)."
    )
    return FakeEmbedder(dimensions=settings.embedding_dimensions)
