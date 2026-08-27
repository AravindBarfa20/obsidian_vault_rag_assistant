---
title: Semantic Search
tags: [ai, retrieval, search]
---

# Semantic Search

Semantic search retrieves passages by meaning rather than exact word overlap.
The question and document chunks are converted into [[Embeddings]], then the
nearest vectors are selected from the [[Vector Database]].

## Asymmetric retrieval

A user question and a reference passage play different roles. The embedding
model uses `RETRIEVAL_QUERY` for questions and `RETRIEVAL_DOCUMENT` for note
chunks. These task types help the model place a short query near a longer
passage that answers it.

## Where keyword search still helps

Dense vectors are strong for paraphrases but can miss exact identifiers,
acronyms, error codes, and rare names. Keyword search is strong at those exact
matches. A mature system can combine both signals through [[Hybrid Retrieval]].

## Quality controls

Retrieval should oversample candidates before applying the relevance gate and
diversity rules. Capping chunks per note stops one long document from occupying
the entire context window.
