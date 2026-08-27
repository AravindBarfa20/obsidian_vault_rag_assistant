---
title: RAG Evaluation
tags: [ai, evaluation]
---

# RAG Evaluation

Evaluating a RAG system means measuring both retrieval and generation. See
[[RAG]].

## Metrics

The metrics I track are:

- **Retrieval relevance**: did we retrieve the chunks that actually contain the
  answer (recall@k, precision@k).
- **Source correctness**: does the cited note match the expected source note.
- **Answer faithfulness**: is every claim in the answer supported by the
  retrieved context, with no hallucination.
- **Answer relevance**: does the answer actually address the question.

## Approach

I use a small labelled question set where each question has an expected source
note, then check whether retrieval surfaces that note and whether the answer is
faithful to it.
