---
title: RAG
tags: [ai, retrieval, core]
---

# RAG

Retrieval-Augmented Generation (RAG) is an architecture that grounds a language
model's answers in an external knowledge source. Instead of relying only on the
model's parametric memory, RAG first retrieves relevant documents and then
conditions generation on them. This relates to [[Embeddings]] and the
[[Vector Database]].

## How it works

The pipeline is: chunk documents, embed them, store the vectors, retrieve the
top matches for a query, and pass that context to the LLM to generate a
grounded answer.

## Why it matters

RAG reduces hallucination because the model is instructed to answer from
retrieved context. When the context does not contain the answer, a well-built
system says so rather than inventing facts.
