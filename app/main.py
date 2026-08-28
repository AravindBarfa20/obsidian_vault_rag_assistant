"""FastAPI application entrypoint.

Wires logging, CORS, domain-error handling and the API routes. Kept thin: all
behaviour lives in the layered services, so this file is composition only.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.dependencies import Container, IndexingStatus
from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.core.logging import configure_logging, get_logger
from app.ingestion.loader import resolve_vault_dir
from app.ingestion.pipeline import ingest_vault


async def _prepare_empty_index(app: FastAPI, logger) -> None:
    """Build a missing local index without delaying the first page load."""
    container: Container = app.state.container
    status: IndexingStatus = app.state.indexing_status
    try:
        vault_dir = resolve_vault_dir(container.settings, None)
        report = await asyncio.to_thread(
            ingest_vault,
            vault_dir,
            container.store,
            container.embedder,
            container.settings,
        )
    except Exception as exc:  # surfaced through /health and the UI
        status.fail(exc)
        logger.exception("Initial vault indexing failed")
    else:
        status.complete()
        logger.info("Initial vault indexing complete: %d chunks", report.chunks_written)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app")

    app = FastAPI(
        title="Obsidian Vault RAG Knowledge Assistant",
        version="1.0.0",
        description=(
            "Retrieval-augmented QA over an Obsidian Markdown vault. "
            "Answers are grounded in retrieved notes with source attribution."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Build services eagerly so misconfiguration surfaces at startup, not on the
    # first request.
    app.state.container = Container(settings)
    app.state.indexing_status = IndexingStatus()

    @app.on_event("startup")
    async def prepare_empty_index() -> None:
        """Serve the UI immediately, then prepare an empty ephemeral index."""
        container: Container = app.state.container
        if container.store.count() > 0:
            return
        app.state.indexing_status.begin()
        app.state.index_task = asyncio.create_task(_prepare_empty_index(app, logger))

    @app.exception_handler(RAGError)
    async def handle_rag_error(_: Request, exc: RAGError) -> JSONResponse:
        logger.warning("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code},
        )

    app.include_router(router)

    # Keep the frontend dependency-free and serve it from the same origin as
    # the API. This avoids a second dev server and any production CORS coupling.
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def frontend() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    logger.info(
        "App ready (embeddings=%s, gemini_configured=%s)",
        settings.embedding_model,
        settings.has_gemini_key,
    )
    return app


app = create_app()
