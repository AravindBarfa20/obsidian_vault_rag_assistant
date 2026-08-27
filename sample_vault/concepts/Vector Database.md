---
title: Vector Database
tags: [infrastructure, retrieval]
---

# Vector Database

A vector database stores embeddings and supports fast nearest-neighbour search
over them. It is not the same thing as the embedding model or the LLM; it only
stores and searches vectors. See [[Embeddings]].

## ChromaDB

ChromaDB is a lightweight open-source vector database. It supports persistence,
metadata filtering, and cosine similarity search, which makes it a good fit for
a local RAG prototype.
