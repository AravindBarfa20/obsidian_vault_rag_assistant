"""Obsidian-flavoured Markdown parsing.

Turns a RawNote into a ParsedNote: frontmatter, structural blocks, tags and
wikilinks. Nothing here knows about chunk sizes or embeddings -- structure is
recovered first, and only afterwards packed into chunks.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from app.core.logging import get_logger
from app.models.documents import BlockKind, MarkdownBlock, ParsedNote, RawNote

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
# An Obsidian tag is #word (no space after #), which is what distinguishes it
# from an ATX heading. Nested tags (#area/rag) are kept whole.
_TAG_RE = re.compile(r"(?<![\w&/#])#([A-Za-z][\w-]*(?:/[\w-]+)*)")
# [[Target]], [[Target|alias]], [[Target#Section]], ![[embed]]
_WIKILINK_RE = re.compile(r"!?\[\[([^\]\[|#]+)(?:#[^\]\[|]*)?(?:\|[^\]\[]*)?\]\]")


def split_frontmatter(content: str) -> tuple[dict[str, Any], str, int]:
    """Return (frontmatter, body, lines_consumed).

    Malformed YAML is tolerated: the note is still ingested, just without
    structured frontmatter, since a broken header should never lose a note.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content, 0
    raw = match.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        logger.warning("Skipping malformed YAML frontmatter")
        data = None
    body = content[match.end() :]
    consumed = content[: match.end()].count("\n")
    return (data if isinstance(data, dict) else {}), body, consumed


def extract_wikilinks(text: str) -> list[str]:
    """Obsidian wikilink targets, de-duplicated, order preserved."""
    seen: dict[str, None] = {}
    for target in _WIKILINK_RE.findall(text):
        cleaned = target.strip()
        if cleaned:
            seen.setdefault(cleaned, None)
    return list(seen)


def extract_tags(frontmatter: dict[str, Any], prose: str) -> list[str]:
    """Tags from frontmatter plus inline #tags found outside code blocks."""
    seen: dict[str, None] = {}

    raw = frontmatter.get("tags") or frontmatter.get("tag")
    if isinstance(raw, str):
        candidates = re.split(r"[,\s]+", raw)
    elif isinstance(raw, (list, tuple)):
        candidates = [str(item) for item in raw]
    else:
        candidates = []
    for tag in candidates:
        cleaned = tag.strip().lstrip("#")
        if cleaned:
            seen.setdefault(cleaned, None)

    for tag in _TAG_RE.findall(prose):
        seen.setdefault(tag, None)
    return list(seen)


def _classify(line: str) -> BlockKind:
    if _LIST_RE.match(line):
        return "list"
    if line.lstrip().startswith(">"):
        return "quote"
    if line.lstrip().startswith("|"):
        return "table"
    return "paragraph"


def split_blocks(body: str, line_offset: int = 0) -> list[MarkdownBlock]:
    """Split a note body into structural blocks, tracking the heading path.

    Rules that matter for retrieval quality:
      * headings are not emitted as blocks; they become the breadcrumb carried
        by every block beneath them, so section context is never orphaned;
      * a fenced code block is one atomic block, blank lines included, so code
        is never cut in half by chunking downstream.
    """
    blocks: list[MarkdownBlock] = []
    heading_path: list[str] = []
    buffer: list[str] = []
    buffer_start = 0

    def flush() -> None:
        nonlocal buffer, buffer_start
        text = "\n".join(buffer).strip()
        if text:
            blocks.append(
                MarkdownBlock(
                    kind=_classify(buffer[0]),
                    text=text,
                    heading_path=tuple(heading_path),
                    line_start=buffer_start + line_offset,
                )
            )
        buffer = []

    lines = body.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]

        fence = _FENCE_RE.match(line)
        if fence:
            flush()
            marker = fence.group(1)[0] * 3
            code_lines = [line]
            index += 1
            while index < len(lines):
                code_lines.append(lines[index])
                if lines[index].strip().startswith(marker):
                    index += 1
                    break
                index += 1
            blocks.append(
                MarkdownBlock(
                    kind="code",
                    text="\n".join(code_lines).strip(),
                    heading_path=tuple(heading_path),
                    line_start=index + line_offset,
                )
            )
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            del heading_path[level - 1 :]
            while len(heading_path) < level - 1:
                heading_path.append("")  # skipped level, keep depth consistent
            heading_path.append(title)
            index += 1
            continue

        if not line.strip():
            flush()
            index += 1
            continue

        if not buffer:
            buffer_start = index
        buffer.append(line)
        index += 1

    flush()
    return blocks


def parse_note(note: RawNote) -> ParsedNote:
    """Full parse of one note. Pure function -- no I/O, easy to test."""
    frontmatter, body, consumed = split_frontmatter(note.content)
    blocks = split_blocks(body, line_offset=consumed)

    # Tags and wikilinks are read from prose only: a '#tag' inside a code fence
    # is a comment or a CSS id, not an Obsidian tag.
    prose = "\n".join(b.text for b in blocks if b.kind != "code")
    tags = extract_tags(frontmatter, prose)
    wikilinks = extract_wikilinks(prose)

    return ParsedNote(
        note=note,
        blocks=tuple(blocks),
        tags=tuple(tags),
        wikilinks=tuple(wikilinks),
        frontmatter=frontmatter,
    )
