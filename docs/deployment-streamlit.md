# Deploy on Streamlit Community Cloud

This project can run as a single Streamlit app using the same RAG services as
the FastAPI deployment. The Streamlit entrypoint is `streamlit_app.py`.

## 1. Create the app

1. Sign in at [share.streamlit.io](https://share.streamlit.io).
2. Select **Create app** and choose this GitHub repository's `main` branch.
3. Set the main file path to `streamlit_app.py`.
4. Choose a clear app URL, such as `obsidian-vault-rag-assistant`.

## 2. Add secrets

Before deploying, open **App settings → Secrets** and paste:

```toml
GEMINI_API_KEY = "your-production-Gemini-key"
GROQ_API_KEY = "gsk_your-production-Groq-key"
GENERATION_PROVIDER = "groq"
GROQ_MODEL = "qwen/qwen3.6-27b"
```

The keys are stored by Streamlit and are never committed to Git. Gemini is used
for embeddings/indexing; Groq generates the grounded answer. Use separate
deployment keys, not a local `.env` file.

## 3. What to expect on free hosting

The app creates the sample-vault index on a new running instance. The UI shows
an explicit preparation spinner during that one-time step. Indexing is
incremental while the instance stays active; a free hosted instance can sleep,
so its next cold start may need to recreate the temporary local index.

## 4. Verify

After the app is live, ask:

> What is RAG and why is retrieval important?

You should see a grounded answer plus expandable cited passages from the sample
vault. A provider `503` means the upstream model is temporarily busy, not that
the vault index has failed.
