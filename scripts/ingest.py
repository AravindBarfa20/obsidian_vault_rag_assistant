"""CLI ingestion: build or refresh the vector index without running the API.

    python -m scripts.ingest [--vault PATH] [--force]

Useful in local dev, CI, and (critically) as a build-time step for serverless
deployment, where ingestion should not run inside a request handler.
"""

from __future__ import annotations

import argparse

from app.api.dependencies import Container
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ingestion.loader import resolve_vault_dir
from app.ingestion.pipeline import ingest_vault


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an Obsidian vault.")
    parser.add_argument("--vault", default=None, help="Vault directory to ingest.")
    parser.add_argument("--force", action="store_true", help="Full rebuild.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    container = Container(settings)

    vault_dir = resolve_vault_dir(settings, args.vault)
    report = ingest_vault(
        vault_dir=vault_dir,
        store=container.store,
        embedder=container.embedder,
        settings=settings,
        force=args.force,
    )
    print("\n=== Ingestion report ===")
    for key, value in report.__dict__.items():
        print(f"{key:26}: {value}")


if __name__ == "__main__":
    main()
