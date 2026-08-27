"""Deterministic, dependency-free embedder for tests and offline development.

A hashed bag-of-words projected onto a fixed-dimensional unit sphere. It is not
semantically strong, but it is deterministic and gives non-trivial cosine
structure (documents sharing words score higher), which is exactly what the
retrieval and no-answer tests need -- with no API key and no network.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Content-word filter. The offline embedder has no notion of meaning, so common
# function words -- which collide heavily in hash space -- would otherwise
# dominate cosine similarity and make an off-topic query look relevant. Dropping
# them makes the deterministic heuristic behave enough like semantic search for
# the retrieval and no-answer tests to be meaningful.
_STOPWORDS = frozenset(
    """a an the of to in on for and or is are was were be been being do does did
    how what when where why who which that this these those it its as at by with
    from into about my your our their his her i you we they me us them can could
    should would will shall may might must have has had not no yes if then than
    over under out up down best most more some any all""".split()
)


class FakeEmbedder:
    def __init__(self, dimensions: int = 256, model_name: str = "fake-embedder") -> None:
        self._dimensions = dimensions
        self._model = model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def recommended_threshold(self) -> float:
        # The hashed bag-of-words scale is lower than a real model's; this keeps
        # offline retrieval usable while still rejecting off-topic queries.
        return 0.30

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for token in _TOKEN_RE.findall(text.lower()):
            if len(token) <= 2 or token in _STOPWORDS:
                continue
            digest = hashlib.md5(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
