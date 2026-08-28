"""Central, explicit application configuration.

Every knob that changes RAG behaviour lives here so that tuning the system is a
config exercise rather than a code hunt. Values come from the environment (or a
local .env file); secrets are never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Gemini -----------------------------------------------------------
    gemini_api_key: str = Field(default="", description="Google AI Studio API key.")
    # Current generally-available Gemini embedding model. Matryoshka-capable:
    # `embedding_dimensions` truncates the 3072-d output to a cheaper size.
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 32
    # Generation is independently swappable; embeddings stay on Gemini so a
    # provider change never invalidates the existing vector index.
    generation_provider: str = "auto"
    llm_model: str = "gemini-3.7-flash"
    groq_api_key: str = Field(default="", description="Groq API key for generation.")
    groq_model: str = "qwen/qwen3.6-27b"
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 2048

    # --- Vault ------------------------------------------------------------
    # Hard boundary for filesystem access: an ingest request may only name this
    # directory or something inside it. See app/ingestion/loader.py.
    vault_dir: Path = Path("./sample_vault")
    max_file_bytes: int = 2_000_000
    ignored_dirs: tuple[str, ...] = (
        ".obsidian",
        ".trash",
        ".git",
        ".github",
        "node_modules",
        "__pycache__",
        ".DS_Store",
    )

    # --- Chunking ---------------------------------------------------------
    # Sizes are in characters; ~4 chars/token for English prose.
    chunk_size: int = 1400
    chunk_overlap: int = 200
    min_chunk_size: int = 120

    # --- Vector store -----------------------------------------------------
    chroma_dir: Path = Path("./.chroma")
    collection_name: str = "obsidian_vault"

    # --- Retrieval --------------------------------------------------------
    top_k: int = 6
    # Cosine relevance in [0, 1]; below this a chunk is not considered evidence.
    # None means "use the active embedding provider's recommended threshold",
    # which keeps the gate calibrated whether running on Gemini or offline.
    relevance_threshold: float | None = None
    # Oversample before filtering/diversifying so the threshold has candidates
    # to work with.
    candidate_multiplier: int = 4
    # Cap chunks contributed by any single note so one long note cannot crowd
    # out the rest of the vault.
    max_chunks_per_note: int = 3

    # --- Generation -------------------------------------------------------
    # Follow-up questions are rewritten into standalone queries before retrieval.
    enable_query_condensation: bool = True
    max_history_turns: int = 6

    # --- App --------------------------------------------------------------
    log_level: str = "INFO"
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")

    @field_validator("vault_dir", "chroma_dir")
    @classmethod
    def _resolve(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("relevance_threshold", mode="before")
    @classmethod
    def _blank_threshold_uses_provider_default(cls, value: object) -> object:
        """Treat an empty env value as None, as documented in `.env.example`."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("generation_provider")
    @classmethod
    def _validate_generation_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider not in {"auto", "gemini", "groq"}:
            raise ValueError("GENERATION_PROVIDER must be auto, gemini, or groq.")
        return provider

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton (also the FastAPI dependency)."""
    return Settings()
