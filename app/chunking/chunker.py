"""Structure-aware chunking.

Blocks are packed into chunks rather than the note being cut at fixed character
offsets. Two invariants drive the design:

  1. A chunk never spans two different sections. Mixing "Evaluation" with
     "Limitations" in one vector blurs both, and makes section attribution a
     lie.
  2. A chunk carries its heading breadcrumb, so a retrieved bullet list still
     knows it lives under "RAG > Evaluation".

Overlap is applied only *within* a section, where continuation is real.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.models.documents import Chunk, MarkdownBlock, ParsedNote, make_chunk_id

logger = get_logger(__name__)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _split_oversized(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Last-resort split for a single block larger than chunk_size.

    Prefers paragraph boundaries, then sentence boundaries, and only slices
    mid-sentence when a single sentence is itself too long.
    """
    units = [u for u in re.split(r"\n{2,}", text) if u.strip()]
    if len(units) == 1:
        units = [u for u in _SENTENCE_RE.split(text) if u.strip()]

    parts: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > chunk_size:  # unsplittable run (long code line, table)
            if current:
                parts.append(current)
                current = ""
            step = chunk_size - overlap
            parts.extend(unit[i : i + chunk_size] for i in range(0, len(unit), step))
            continue
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) > chunk_size and current:
            parts.append(current)
            current = unit
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def _overlap_tail(text: str, overlap: int) -> str:
    """Tail of the previous chunk, snapped to a sentence/line boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return text if overlap > 0 else ""
    tail = text[-overlap:]
    for boundary in ("\n\n", "\n", ". "):
        position = tail.find(boundary)
        if 0 <= position < len(tail) - 20:
            return tail[position + len(boundary) :].strip()
    return tail.strip()


def _pack_section(
    blocks: list[MarkdownBlock], chunk_size: int, overlap: int
) -> list[str]:
    """Greedily pack one section's blocks into chunk-sized texts."""
    texts: list[str] = []
    current = ""
    for block in blocks:
        piece = block.text
        if len(piece) > chunk_size:
            if current:
                texts.append(current)
                current = ""
            texts.extend(_split_oversized(piece, chunk_size, overlap))
            continue
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) > chunk_size and current:
            texts.append(current)
            carry = _overlap_tail(current, overlap)
            current = f"{carry}\n\n{piece}" if carry else piece
        else:
            current = candidate
    if current:
        texts.append(current)
    return texts


def chunk_note(
    parsed: ParsedNote,
    chunk_size: int,
    chunk_overlap: int,
    min_chunk_size: int,
) -> list[Chunk]:
    """Chunk a parsed note, preserving section boundaries and metadata."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    # Group consecutive blocks by their heading breadcrumb.
    sections: list[tuple[tuple[str, ...], list[MarkdownBlock]]] = []
    for block in parsed.blocks:
        if sections and sections[-1][0] == block.heading_path:
            sections[-1][1].append(block)
        else:
            sections.append((block.heading_path, [block]))

    chunks: list[Chunk] = []
    for heading_path, blocks in sections:
        section = " > ".join(part for part in heading_path if part)
        for text in _pack_section(blocks, chunk_size, chunk_overlap):
            text = text.strip()
            if not text:
                continue
            # A stub too small to stand alone is folded into the previous chunk
            # of the same section rather than becoming a noisy vector.
            if (
                len(text) < min_chunk_size
                and chunks
                and chunks[-1].section == section
                and len(chunks[-1].text) + len(text) <= chunk_size * 1.5
            ):
                previous = chunks.pop()
                text = f"{previous.text}\n\n{text}"
                index = previous.chunk_index
            else:
                index = len(chunks)
            chunks.append(
                Chunk(
                    id=make_chunk_id(parsed.note.rel_path, index),
                    text=text,
                    rel_path=parsed.note.rel_path,
                    title=parsed.note.title,
                    section=section,
                    chunk_index=index,
                    tags=parsed.tags,
                    wikilinks=parsed.wikilinks,
                    content_hash=parsed.note.content_hash,
                )
            )

    # Re-index defensively so ids stay dense and stable after any folding.
    return [
        Chunk(
            **{
                **chunk.__dict__,
                "chunk_index": position,
                "id": make_chunk_id(chunk.rel_path, position),
            }
        )
        for position, chunk in enumerate(chunks)
    ]
