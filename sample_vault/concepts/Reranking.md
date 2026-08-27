---
title: Reranking
tags: [ai, retrieval, quality]
---

# Reranking

Reranking applies a more precise model to a small candidate set after the fast
initial search. The first retriever optimizes recall; the reranker improves the
order and precision of the passages sent to generation.

## Cross-encoder approach

A cross-encoder reads the question and candidate passage together, allowing
deeper token-level comparison than independent embeddings. It is more accurate
but slower, which is why it should score only an oversampled shortlist rather
than the entire vault.

## MVP decision

The current assistant uses thresholding and per-note diversity instead of a
reranker. This keeps latency and infrastructure low. A reranker becomes
justified when [[RAG Evaluation]] shows that the correct note appears in top-k
but frequently fails to rank first.

## Measurement

The useful before-and-after measures are top-source accuracy, mean reciprocal
rank, answer latency, and generation cost. Quality gains should be compared
against the additional request time.
