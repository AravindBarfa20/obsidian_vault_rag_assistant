"""Minimal logging setup.

Deliberately plain stdlib logging: enough structure to trace an ingest or a
query end-to-end, no logging framework to explain.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:  # idempotent under uvicorn --reload
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)-28s %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
