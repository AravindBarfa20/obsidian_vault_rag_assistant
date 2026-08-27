"""Ingestion orchestration: load -> parse -> chunk -> embed -> upsert.

Incremental by default: a note whose content hash already matches the index is
skipped, so unchanged files are never re-embedded. A note that has shrunk has
its stale trailing chunks deleted before the new ones are written.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from app.chunking.chunker import chunk_note
from app.core.config import Settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider
from app.ingestion.loader import load_vault
from app.models.documents import Chunk
from app.parsing.markdown_parser import parse_note
from app.vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


@dataclass
class IngestReport:
    vault_dir: str
    notes_total: int = 0
    notes_ingested: int = 0
    notes_skipped_unchanged: int = 0
    notes_empty: int = 0
    chunks_written: int = 0
    embedding_model: str = ""
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


def _chunks_for_note(note, settings: Settings) -> list[Chunk]:
    parsed = parse_note(note)
    return chunk_note(
        parsed,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        min_chunk_size=settings.min_chunk_size,
    )


def ingest_vault(
    vault_dir: Path,
    store: ChromaStore,
    embedder: EmbeddingProvider,
    settings: Settings,
    force: bool = False,
) -> IngestReport:
    """Ingest (or refresh) a vault into the vector store."""
    started = time.perf_counter()
    report = IngestReport(vault_dir=str(vault_dir), embedding_model=embedder.model_name)

    if force:
        store.reset()
    existing = {} if force else store.existing_hashes()

    notes = load_vault(vault_dir, settings)
    report.notes_total = len(notes)

    pending_chunks: list[Chunk] = []
    for note in notes:
        if existing.get(note.rel_path) == note.content_hash:
            report.notes_skipped_unchanged += 1
            continue
        try:
            chunks = _chunks_for_note(note, settings)
        except Exception as exc:  # a bad note must not abort the whole ingest
            logger.exception("Failed to chunk %s", note.rel_path)
            report.errors.append(f"{note.rel_path}: {exc}")
            continue
        if not chunks:
            report.notes_empty += 1
            continue
        # Clear any prior chunks for this note so an edit never leaves orphans.
        store.delete_note(note.rel_path)
        pending_chunks.extend(chunks)
        report.notes_ingested += 1

    if pending_chunks:
        embeddings = embedder.embed_documents([c.embedding_text for c in pending_chunks])
        store.upsert_chunks(pending_chunks, embeddings)
        report.chunks_written = len(pending_chunks)

    report.duration_seconds = round(time.perf_counter() - started, 3)
    logger.info(
        "Ingest done: %d ingested, %d unchanged, %d chunks in %.2fs",
        report.notes_ingested,
        report.notes_skipped_unchanged,
        report.chunks_written,
        report.duration_seconds,
    )
    return report
