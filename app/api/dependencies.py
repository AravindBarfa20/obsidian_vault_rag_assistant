"""Dependency wiring.

Heavy singletons (vector store, embedder, LLM) are built once and cached on the
FastAPI app state, so each request reuses one Chroma client and one Gemini
client rather than reconstructing them.
"""

from __future__ import annotations

from threading import Lock

from fastapi import Request

from app.core.config import Settings, get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import build_embedder
from app.generation.answer_service import AnswerService
from app.generation.llm_factory import LLM, build_llm
from app.retrieval.retriever import Retriever
from app.vectorstore.chroma_store import ChromaStore


class IndexingStatus:
    """Thread-safe status shared by background and request-driven ingestion."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = "ready"
        self._error: str | None = None

    def begin(self) -> bool:
        """Mark an ingestion as running, unless another ingestion owns it."""
        with self._lock:
            if self._state == "indexing":
                return False
            self._state = "indexing"
            self._error = None
            return True

    def complete(self) -> None:
        with self._lock:
            self._state = "ready"
            self._error = None

    def fail(self, error: Exception) -> None:
        with self._lock:
            self._state = "failed"
            self._error = str(error) or "The vault could not be indexed."

    def snapshot(self) -> tuple[str, str | None]:
        with self._lock:
            return self._state, self._error


class Container:
    """Lazily-constructed application services."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._store: ChromaStore | None = None
        self._embedder: EmbeddingProvider | None = None
        self._llm: LLM | None = None

    @property
    def store(self) -> ChromaStore:
        if self._store is None:
            self._store = ChromaStore(
                self.settings.chroma_dir, self.settings.collection_name
            )
        return self._store

    @property
    def embedder(self) -> EmbeddingProvider:
        if self._embedder is None:
            self._embedder = build_embedder(self.settings)
        return self._embedder

    @property
    def llm(self) -> LLM:
        if self._llm is None:
            self._llm = build_llm(self.settings)
        return self._llm

    @property
    def retriever(self) -> Retriever:
        return Retriever(self.store, self.embedder, self.settings)

    @property
    def answer_service(self) -> AnswerService:
        return AnswerService(self.retriever, self.llm, self.settings)


def get_container(request: Request) -> Container:
    container: Container | None = getattr(request.app.state, "container", None)
    if container is None:
        container = Container(get_settings())
        request.app.state.container = container
    return container


def get_indexing_status(request: Request) -> IndexingStatus:
    status: IndexingStatus | None = getattr(request.app.state, "indexing_status", None)
    if status is None:
        status = IndexingStatus()
        request.app.state.indexing_status = status
    return status
