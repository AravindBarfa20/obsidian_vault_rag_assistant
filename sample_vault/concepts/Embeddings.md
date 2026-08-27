---
title: Embeddings
tags: [ai, retrieval]
---

# Embeddings

An embedding is a dense vector that represents the meaning of a piece of text.
Texts with similar meaning map to nearby vectors, which is what makes semantic
search possible. See [[RAG]] and [[Vector Database]].

## Similarity

Cosine similarity is the usual way to compare two embeddings. A value near 1
means the texts are semantically close; a value near 0 means unrelated.

## Task types

Good retrieval embedding models distinguish a document embedding from a query
embedding, which improves retrieval quality for asymmetric search.
