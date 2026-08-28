"""Domain errors.

Each carries an HTTP status so the API layer can translate failures into useful
messages instead of leaking stack traces.
"""

from __future__ import annotations


class RAGError(Exception):
    """Base class for all expected application failures."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VaultError(RAGError):
    """Vault path is missing, unreadable, or outside the allowed root."""

    status_code = 400
    code = "vault_error"


class ConfigurationError(RAGError):
    """The server is missing configuration required for this operation."""

    status_code = 503
    code = "configuration_error"


class EmbeddingError(RAGError):
    """The embedding provider failed."""

    status_code = 502
    code = "embedding_error"


class GenerationError(RAGError):
    """The LLM call failed."""

    status_code = 502
    code = "generation_error"


class VectorStoreError(RAGError):
    """The vector database failed or is not yet populated."""

    status_code = 500
    code = "vectorstore_error"


class IndexingInProgressError(RAGError):
    """The vault is being prepared and cannot answer queries yet."""

    status_code = 503
    code = "indexing_in_progress"
