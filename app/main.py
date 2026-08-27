"""FastAPI application entrypoint.

Wires logging, CORS, domain-error handling and the API routes. Kept thin: all
behaviour lives in the layered services, so this file is composition only.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import Container
from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import RAGError
from app.core.logging import configure_logging, get_logger


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

    @app.exception_handler(RAGError)
    async def handle_rag_error(_: Request, exc: RAGError) -> JSONResponse:
        logger.warning("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code},
        )

    app.include_router(router)
    logger.info(
        "App ready (embeddings=%s, gemini_configured=%s)",
        settings.embedding_model,
        settings.has_gemini_key,
    )
    return app


app = create_app()
