"""HTTP routes: /ingest, /query, /sources, /health."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import Container, get_container
from app.core.logging import get_logger
from app.ingestion.loader import resolve_vault_dir
from app.ingestion.pipeline import ingest_vault
from app.models.api import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceSummary,
    SourcesResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(container: Container = Depends(get_container)) -> HealthResponse:
    settings = container.settings
    try:
        indexed = container.store.count()
    except Exception:  # health must not throw even if the store is unavailable
        indexed = -1
    return HealthResponse(
        status="ok",
        embedding_provider=container.embedder.model_name,
        llm_provider=container.llm.model_name,
        gemini_configured=settings.has_gemini_key,
        indexed_chunks=indexed,
        collection=settings.collection_name,
    )


@router.post("/ingest", response_model=IngestResponse, tags=["ingestion"])
def ingest(
    payload: IngestRequest, container: Container = Depends(get_container)
) -> IngestResponse:
    settings = container.settings
    vault_dir = resolve_vault_dir(settings, payload.vault_path)
    report = ingest_vault(
        vault_dir=vault_dir,
        store=container.store,
        embedder=container.embedder,
        settings=settings,
        force=payload.force,
    )
    return IngestResponse(**report.__dict__)


@router.post("/query", response_model=QueryResponse, tags=["query"])
def query(
    payload: QueryRequest, container: Container = Depends(get_container)
) -> QueryResponse:
    result = container.answer_service.answer(
        question=payload.question,
        history=[t.model_dump() for t in payload.history],
        top_k=payload.top_k,
        threshold=payload.threshold,
        tag=payload.tag,
    )
    return QueryResponse(
        answer=result.answer,
        grounded=result.grounded,
        sources=[s.__dict__ for s in result.sources],
        query_used=result.query_used,
        model=result.model,
    )


@router.get("/sources", response_model=SourcesResponse, tags=["query"])
def sources(container: Container = Depends(get_container)) -> SourcesResponse:
    rows = container.store.list_sources()
    return SourcesResponse(
        notes=[
            SourceSummary(
                source=row["source"],
                title=row["title"],
                path=row["rel_path"],
                chunks=row["chunks"],
                tags=row["tags"],
            )
            for row in rows
        ],
        total_notes=len(rows),
        total_chunks=sum(row["chunks"] for row in rows),
    )
