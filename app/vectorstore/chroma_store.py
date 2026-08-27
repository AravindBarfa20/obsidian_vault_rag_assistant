"""ChromaDB vector store wrapper.

Responsibilities kept narrow and separate from embedding/LLM concerns:
  * persist chunk vectors + text + metadata under stable ids;
  * upsert by id so re-ingesting an edited note replaces its chunks in place
    (no duplicate accumulation);
  * incremental ingestion support via a per-note content hash;
  * cosine similarity search returning normalised relevance in [0, 1].

Vectors are supplied by us (embedding_function=None) to keep the embedding
provider swappable and explicit -- Chroma never calls an embedding model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Chroma 0.6.x fires a telemetry event on client start that crashes noisily on
# some builds; disabling it keeps logs clean and avoids the network call.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
# Chroma imports ONNX Runtime through its local embedding dependencies. Disable
# ORT telemetry before that import so it does not attempt to persist a device id.
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger
from app.models.documents import Chunk, RetrievedChunk

logger = get_logger(__name__)


class ChromaStore:
    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        try:
            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:  # pragma: no cover - infra failure
            raise VectorStoreError(f"Could not open vector store: {exc}") from exc
        self._name = collection_name

    # --- write path -------------------------------------------------------
    def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise VectorStoreError("chunk/embedding count mismatch")
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[c.to_metadata() for c in chunks],
        )
        logger.info("Upserted %d chunks into '%s'", len(chunks), self._name)

    def delete_note(self, rel_path: str) -> None:
        """Remove every chunk belonging to a note (used when a note shrinks)."""
        self._collection.delete(where={"rel_path": rel_path})

    def existing_hashes(self) -> dict[str, str]:
        """Map rel_path -> content_hash for notes already indexed.

        Lets ingestion skip unchanged files instead of re-embedding them.
        """
        data = self._collection.get(include=["metadatas"])
        hashes: dict[str, str] = {}
        for meta in data.get("metadatas") or []:
            rel = meta.get("rel_path")
            if rel:
                hashes[rel] = meta.get("content_hash", "")
        return hashes

    # --- read path --------------------------------------------------------
    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        # Chroma logs a warning when n_results exceeds the number of indexed
        # chunks. Cap the request for small/new vaults while preserving the
        # retriever's oversampling behaviour as the collection grows.
        collection_size = self._collection.count()
        if collection_size == 0:
            return []
        n_results = min(max(1, top_k), collection_size)
        try:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:  # pragma: no cover
            raise VectorStoreError(f"Query failed: {exc}") from exc

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        retrieved: list[RetrievedChunk] = []
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            # Chroma cosine distance is in [0, 2]; relevance = 1 - distance,
            # clamped to [0, 1] so thresholds are interpretable.
            relevance = max(0.0, min(1.0, 1.0 - float(dist)))
            retrieved.append(
                RetrievedChunk(
                    chunk_id=cid, text=doc, metadata=dict(meta), relevance=relevance
                )
            )
        return retrieved

    # --- introspection ----------------------------------------------------
    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> list[dict[str, Any]]:
        """One row per note currently indexed, with chunk counts."""
        data = self._collection.get(include=["metadatas"])
        by_note: dict[str, dict[str, Any]] = {}
        for meta in data.get("metadatas") or []:
            rel = meta.get("rel_path", "unknown")
            row = by_note.setdefault(
                rel,
                {
                    "rel_path": rel,
                    "source": meta.get("source", rel),
                    "title": meta.get("title", rel),
                    "chunks": 0,
                    "tags": meta.get("tags", ""),
                },
            )
            row["chunks"] += 1
        return sorted(by_note.values(), key=lambda r: r["rel_path"])

    def reset(self) -> None:
        """Drop and recreate the collection (full rebuild)."""
        self._client.delete_collection(self._name)
        self._collection = self._client.get_or_create_collection(
            name=self._name, metadata={"hnsw:space": "cosine"}
        )
        logger.info("Reset collection '%s'", self._name)
