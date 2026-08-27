---
title: Chunking Strategies
tags: [ai, retrieval, ingestion]
---

# Chunking Strategies

Chunking decides what unit of a note can be retrieved. A useful chunk must be
small enough to stay focused but complete enough to preserve the fact needed by
the answer. Chunking therefore affects both retrieval precision and generation
quality. See [[RAG]] and [[Semantic Search]].

## Structure before size

Markdown headings are semantic boundaries. I prefer to split a note into
sections first, then pack blocks within each section up to the size limit. This
prevents an unrelated conclusion from being merged with the next topic. Lists
and fenced code blocks should stay intact whenever possible.

Each embedded chunk carries its heading breadcrumb, such as
`Project > Decisions > Storage`. The breadcrumb gives short passages enough
context to be meaningful during semantic search.

## Overlap

Overlap protects facts that fall near a chunk boundary, but excessive overlap
creates duplicate search results and wastes embedding storage. The assistant
uses a modest 200-character overlap within a 1,400-character target chunk.

## Failure modes

Chunks that are too large mix topics and reduce precision. Chunks that are too
small lose definitions and qualifiers. A fixed character split also breaks
lists, code, and heading context, so structure-aware parsing is preferred over
blind slicing.
