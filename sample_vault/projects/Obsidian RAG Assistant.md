---
title: Obsidian RAG Assistant
tags: [project, rag, decisions]
status: active
---

# Obsidian RAG Assistant

The project turns an Obsidian vault into a cited knowledge assistant. Its design
principle is `retrieve → verify → generate → cite`, not question directly to
LLM. The backend uses FastAPI, Gemini embeddings and generation, and ChromaDB.

## Product contract

The assistant must preserve Markdown structure during ingestion, retrieve
relevant passages, answer only from those passages, expose note and section
citations, and decline questions the vault cannot support. Follow-up questions
are rewritten into standalone search queries using recent client-provided
history.

## Engineering decisions

- Embeddings and generation sit behind separate provider interfaces.
- Chroma receives explicit vectors and never chooses the embedding model.
- Stable chunk IDs and note content hashes make ingestion incremental.
- A per-note diversity cap prevents a long note from dominating context.
- The local index is excluded from Git because it is generated runtime data.

See [[Chunking Strategies]], [[Grounding and Hallucination]], and
[[Retrieval Threshold Experiment]].

## Deployment boundary

Local Chroma persistence is appropriate for development and a single persistent
server. A serverless filesystem is ephemeral, so production on Vercel requires
a hosted vector store and a separate ingestion job. The query API itself stays
stateless once the vector store is external.

## Known limitations

The MVP does not yet use wikilinks to expand retrieval, combine keyword and
dense search, or run a cross-encoder reranker. Conversation history is supplied
by the client rather than stored as server-side sessions.
