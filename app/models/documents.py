"""Domain objects that flow through the ingestion pipeline.

    RawNote -> MarkdownBlock[] -> ParsedNote -> Chunk[] -> (vector store)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal

BlockKind = Literal["heading", "paragraph", "list", "code", "quote", "table"]


@dataclass(frozen=True)
class RawNote:
    """A Markdown file read off disk, before any parsing."""

    path: str  # absolute path
    rel_path: str  # path relative to the vault root; the stable note identity
    title: str  # frontmatter title, else H1, else filename stem
    content: str
    content_hash: str  # sha256 of raw bytes; drives incremental ingestion
    modified_at: float


@dataclass(frozen=True)
class MarkdownBlock:
    """One structural unit of a note (a paragraph, a list, a code fence, ...)."""

    kind: BlockKind
    text: str
    # Breadcrumb of enclosing headings, e.g. ["RAG", "Evaluation", "Metrics"].
    heading_path: tuple[str, ...] = ()
    line_start: int = 0


@dataclass(frozen=True)
class ParsedNote:
    """A note after frontmatter, tag, wikilink and structure extraction."""

    note: RawNote
    blocks: tuple[MarkdownBlock, ...]
    tags: tuple[str, ...]
    wikilinks: tuple[str, ...]
    frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """An embeddable unit of text plus the metadata used for attribution."""

    id: str
    text: str
    rel_path: str
    title: str
    section: str  # heading breadcrumb joined with " > "; "" at note root
    chunk_index: int
    tags: tuple[str, ...]
    wikilinks: tuple[str, ...]
    content_hash: str

    @property
    def source(self) -> str:
        """Filename as shown to the user, e.g. "RAG.md"."""
        return self.rel_path.rsplit("/", 1)[-1]

    def to_metadata(self) -> dict[str, str | int]:
        """Chroma accepts only scalar metadata, so sequences are joined."""
        return {
            "rel_path": self.rel_path,
            "source": self.source,
            "title": self.title,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "tags": ",".join(self.tags),
            "wikilinks": ",".join(self.wikilinks),
            "content_hash": self.content_hash,
        }

    @property
    def embedding_text(self) -> str:
        """What actually gets embedded.

        The heading breadcrumb is prepended so a chunk carries its section
        context into vector space: a bare list of metrics under
        "RAG > Evaluation" is far more retrievable when the embedded text says
        so than when it is an anonymous bullet list.
        """
        section = self.section
        # In Obsidian the H1 usually equals the note title; avoid "RAG > RAG > ..".
        if section == self.title:
            section = ""
        elif section.startswith(f"{self.title} > "):
            section = section[len(self.title) + 3 :]
        header = self.title + (f" > {section}" if section else "")
        return f"{header}\n\n{self.text}"


def make_chunk_id(rel_path: str, chunk_index: int) -> str:
    """Stable, collision-resistant id.

    Derived from path + position only (not content), so re-ingesting an edited
    note overwrites its chunks in place rather than accumulating duplicates.
    """
    digest = hashlib.sha1(f"{rel_path}::{chunk_index}".encode()).hexdigest()
    return f"{digest[:16]}"


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by search, with its relevance score."""

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    relevance: float  # cosine relevance in [0, 1]; higher is better

    @property
    def source(self) -> str:
        return str(self.metadata.get("source", "unknown"))

    @property
    def section(self) -> str:
        return str(self.metadata.get("section", ""))

    @property
    def rel_path(self) -> str:
        return str(self.metadata.get("rel_path", ""))

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", self.source))
