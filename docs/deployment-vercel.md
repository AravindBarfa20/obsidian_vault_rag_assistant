# Deployment notes (Vercel target)

The backend is a standard FastAPI ASGI app, which Vercel can serve via a Python
serverless function. Two real constraints must be handled honestly rather than
worked around silently.

## Constraint 1 — ChromaDB persistence is not serverless-durable

`PersistentClient` writes to local disk. On Vercel the function filesystem is
**ephemeral and read-only except `/tmp`**, and `/tmp` is not shared across
invocations or instances. A persisted Chroma directory therefore does **not**
survive between requests in production.

**Recommendation (simplest production-appropriate path):** keep this exact code
and swap only the `ChromaStore` construction for **Chroma Cloud** (managed,
`chromadb.HttpClient`) or a hosted vector DB (Qdrant Cloud, Pinecone). Because
the whole system depends only on the narrow `ChromaStore` surface
(`upsert_chunks`, `query`, `existing_hashes`, `list_sources`), this is a
single-file change — the retrieval, generation and API layers are untouched.

For local development and single-instance/VM deployments (Render, Fly.io,
Railway, a small EC2), the on-disk `PersistentClient` used here is ideal and
needs no change.

## Constraint 2 — ingestion is a long job, not a request handler

Embedding a whole vault can exceed a serverless function's timeout (Vercel's
default is well under what a large vault needs). Do **not** run `/ingest`
inside a serverless request in production.

**Recommendation:** run ingestion as a **build step or a separate job** —
`python -m scripts.ingest` — writing to the managed vector store. The deployed
serverless function then only serves `/query`, `/sources`, `/health`, which are
fast and stateless against the hosted store. The `/ingest` endpoint remains for
local development.

## Summary

| Component | Local dev | Vercel production |
|-----------|-----------|-------------------|
| Vector store | Chroma `PersistentClient` (disk) | Chroma Cloud / Qdrant / Pinecone (`HttpClient`) |
| Ingestion | `/ingest` or `scripts/ingest.py` | build-time / offline job only |
| Query API | uvicorn | serverless function (stateless read) |
| Secrets | `.env` | Vercel environment variables |

No component is silently replaced: the swap points and their reasons are the two
constraints above.
