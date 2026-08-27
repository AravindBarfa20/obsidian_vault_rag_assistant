"""API request/response schemas.

Strongly typed and documented so the schema doubles as the frontend contract
(visible at /docs). These are distinct from the internal domain objects in
documents.py -- the wire format is decoupled from the pipeline's data classes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    vault_path: str | None = Field(
        default=None,
        description="Vault directory to ingest. Relative paths resolve inside "
        "the configured VAULT_DIR; omit to use VAULT_DIR itself.",
    )
    force: bool = Field(
        default=False,
        description="Rebuild the index from scratch instead of incrementally.",
    )


class IngestResponse(BaseModel):
    vault_dir: str
    notes_total: int
    notes_ingested: int
    notes_skipped_unchanged: int
    notes_empty: int
    chunks_written: int
    embedding_model: str
    duration_seconds: float
    errors: list[str]


class ChatTurn(BaseModel):
    role: str = Field(description="'user' or 'assistant'.")
    content: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(
        default_factory=list,
        description="Prior turns, oldest first, for follow-up questions.",
    )
    top_k: int | None = Field(default=None, ge=1, le=20)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    tag: str | None = Field(
        default=None, description="Restrict retrieval to notes carrying this tag."
    )


class SourceModel(BaseModel):
    source: str = Field(description="Note filename, e.g. 'RAG.md'.")
    title: str
    section: str
    path: str
    relevance: float
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    grounded: bool = Field(
        description="False when no vault content met the relevance threshold; "
        "the answer is then the no-answer message."
    )
    sources: list[SourceModel]
    query_used: str
    model: str


class SourceSummary(BaseModel):
    source: str
    title: str
    path: str
    chunks: int
    tags: str


class SourcesResponse(BaseModel):
    notes: list[SourceSummary]
    total_notes: int
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    embedding_provider: str
    llm_provider: str
    gemini_configured: bool
    indexed_chunks: int
    collection: str


class ErrorResponse(BaseModel):
    error: str
    code: str
