---
title: Hybrid Retrieval
tags: [ai, retrieval, search]
---

# Hybrid Retrieval

Hybrid retrieval combines dense semantic search with sparse keyword search.
Dense retrieval finds paraphrases and related concepts; sparse retrieval such
as BM25 preserves exact terms. See [[Semantic Search]] and [[Reranking]].

## Fusion

Each retriever produces its own ranked list. Reciprocal Rank Fusion can combine
the lists without assuming their raw scores share the same scale. A simpler
weighted score is possible, but its weights need evaluation on representative
questions.

## When it is worth adding

Hybrid retrieval is valuable when the vault contains code symbols, ticket IDs,
people's names, or specialized terminology. For a small conceptual demo vault,
dense retrieval alone is a reasonable MVP because it keeps the pipeline easy to
inspect and evaluate.

## Decision

The current assistant deliberately ships dense retrieval first. Hybrid search
is the next retrieval upgrade only after the evaluation set demonstrates exact-
match misses that semantic embeddings cannot solve reliably.
