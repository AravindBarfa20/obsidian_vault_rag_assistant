# Architecture

## RAG pipeline

```mermaid
flowchart TD
    subgraph Ingestion["Ingestion (offline / build-time)"]
        V[Obsidian Vault] --> L[Loader<br/>recursive discovery, path guard]
        L --> P[Markdown Parser<br/>frontmatter, tags, wikilinks, blocks]
        P --> C[Structure-aware Chunker<br/>section-bounded, code-safe]
        C --> E1[Embedding Provider<br/>gemini-embedding-001 / fake]
        E1 --> DB[(ChromaDB<br/>vectors + text + metadata)]
    end

    subgraph Query["Query (request time)"]
        Q[User Question] --> CD{Follow-up?}
        CD -->|has history| Cond[Condense to<br/>standalone query]
        CD -->|no history| QE
        Cond --> QE[Query Embedding]
        QE --> VS[Vector Search<br/>oversample k x m]
        VS --> G{Relevance gate<br/>+ per-note diversity}
        G -->|nothing clears threshold| NA[No-answer<br/>LLM never called]
        G -->|grounded context| GEN[Gemini generation<br/>grounded + cited]
        GEN --> ANS[Answer + Sources]
        NA --> ANS
    end

    DB -.-> VS
```

## Design principle: RETRIEVE → SELECT → GENERATE → CITE

The relevance gate sits **before** the LLM. When no chunk clears the threshold,
the API returns the fixed no-answer message without ever calling Gemini, so
hallucination on empty retrieval is structurally impossible rather than merely
discouraged by prompt wording.

## Layered responsibilities

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Ingestion | `app/ingestion` | Discover + safely load notes; orchestrate ingest |
| Parsing | `app/parsing` | Obsidian Markdown → frontmatter, blocks, tags, wikilinks |
| Chunking | `app/chunking` | Section-aware packing with overlap |
| Embeddings | `app/embeddings` | `EmbeddingProvider` interface + Gemini/fake impls |
| Vector store | `app/vectorstore` | ChromaDB: upsert, query, incremental hashes |
| Retrieval | `app/retrieval` | Embed query, gate, diversify |
| Generation | `app/generation` | Prompt, condensation, Gemini/fake LLM, answer service |
| API | `app/api` | FastAPI routes + dependency wiring |
| Models | `app/models` | Domain dataclasses + API schemas |

The embedding model, the vector database, and the LLM are three separate
interfaces — never conflated. Chroma never calls an embedding model; we supply
vectors explicitly so the provider stays swappable.
