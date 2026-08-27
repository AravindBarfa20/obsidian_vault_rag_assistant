"""Gemini embedding provider (gemini-embedding-001).

Uses asymmetric task types -- RETRIEVAL_DOCUMENT for corpus chunks and
RETRIEVAL_QUERY for questions -- which is the correct, quality-relevant way to
use a retrieval embedding model. Requests are batched and retried with
exponential backoff to survive rate limits without failing an ingest.
"""

from __future__ import annotations

import time

from app.core.exceptions import ConfigurationError, EmbeddingError
from app.core.logging import get_logger
from app.embeddings.base import TaskType

logger = get_logger(__name__)

_TASK_MAP = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-embedding-001",
        dimensions: int = 768,
        batch_size: int = 32,
        max_retries: int = 4,
        recommended_threshold: float = 0.55,
    ) -> None:
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is required for embeddings.")
        from google import genai  # imported lazily so tests run without the SDK path

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self._model = model_name
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._threshold = recommended_threshold

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def recommended_threshold(self) -> float:
        return self._threshold

    def _embed(self, texts: list[str], task: TaskType) -> list[list[float]]:
        from google.genai import types

        config = types.EmbedContentConfig(
            task_type=_TASK_MAP[task],
            output_dimensionality=self._dimensions,
        )
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = self._client.models.embed_content(
                    model=self._model, contents=texts, config=config
                )
                return [list(e.values) for e in response.embeddings]
            except Exception as exc:  # SDK raises provider-specific errors
                last_error = exc
                wait = 2**attempt
                logger.warning(
                    "Embedding attempt %d/%d failed (%s); retrying in %ds",
                    attempt + 1,
                    self._max_retries,
                    type(exc).__name__,
                    wait,
                )
                time.sleep(wait)
        raise EmbeddingError(f"Embedding failed after retries: {last_error}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            vectors.extend(self._embed(batch, "document"))
            logger.info("Embedded %d/%d chunks", len(vectors), len(texts))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]
