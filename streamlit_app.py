"""Streamlit deployment entrypoint for the Obsidian Vault RAG Assistant.

This is a presentation layer only. It intentionally reuses the production
ingestion, retrieval, grounding, and generation services from ``app/`` so the
Streamlit demo has the same RAG behaviour as the FastAPI deployment.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from html import escape

import streamlit as st

from app.api.dependencies import Container
from app.core.config import Settings, get_settings
from app.core.exceptions import RAGError
from app.ingestion.loader import resolve_vault_dir
from app.ingestion.pipeline import ingest_vault


def configure_runtime() -> None:
    """Make Streamlit Cloud secrets available to the existing settings layer."""
    try:
        secrets = st.secrets.to_dict()
    except Exception:
        # Streamlit raises when no secrets.toml exists at all. That is a normal
        # first-deploy condition and is rendered as a helpful setup message.
        return
    if key := secrets.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = str(key)
    if model := secrets.get("LLM_MODEL"):
        os.environ["LLM_MODEL"] = str(model)
    if key := secrets.get("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = str(key)
    if provider := secrets.get("GENERATION_PROVIDER"):
        os.environ["GENERATION_PROVIDER"] = str(provider)
    if model := secrets.get("GROQ_MODEL"):
        os.environ["GROQ_MODEL"] = str(model)


@st.cache_resource(show_spinner=False)
def services() -> tuple[Settings, Container]:
    """Construct the shared services once per running Streamlit process."""
    get_settings.cache_clear()
    settings = get_settings()
    return settings, Container(settings)


def ensure_index(settings: Settings, container: Container, *, refresh: bool = False) -> dict:
    """Create the ephemeral index when a Streamlit instance starts cold."""
    if not refresh and container.store.count() > 0:
        return {"chunks_written": 0, "notes_ingested": 0, "notes_unchanged": 0}
    vault_dir = resolve_vault_dir(settings, None)
    report = ingest_vault(
        vault_dir=vault_dir,
        store=container.store,
        embedder=container.embedder,
        settings=settings,
        force=False,
    )
    return asdict(report)


def source_rows(container: Container) -> list[dict]:
    return container.store.list_sources()


def render_source(source: dict) -> None:
    """Render compact, inspectable evidence for one retrieved passage."""
    relevance = source.get("relevance", 0)
    title = source.get("title", source.get("source", "Source"))
    section = source.get("section") or "Relevant passage"
    with st.expander(f"{title} · {relevance:.0%} match", expanded=False):
        st.caption(f"{source.get('path', '')} › {section}")
        st.write(source.get("snippet", ""))


def inject_style() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Manrope:wght@500;600;700&display=swap');
          :root { --paper:#f6f3eb; --ink:#20201e; --muted:#76736b; --line:#d7d0c3; --sand:#e9dfcd; --accent:#d96e4d; }
          .stApp { background:var(--paper); color:var(--ink); }
          [data-testid="stSidebar"] { background:var(--sand); border-right:1px solid var(--line); }
          [data-testid="stSidebar"] * { color:var(--ink); }
          h1, h2, h3, .stChatMessage p { font-family:'Libre Baskerville', Georgia, serif; }
          h1 { font-size:3.2rem !important; letter-spacing:-.06em; margin-bottom:.15rem !important; }
          p, label, button, [data-testid="stCaptionContainer"] { font-family:'Manrope', sans-serif; }
          [data-testid="stMetricValue"] { font-family:'DM Mono', monospace; font-size:1.5rem; }
          [data-testid="stChatMessage"] { border:1px solid var(--line); border-radius:16px; background:#fcfbf7; padding:.7rem 1rem; }
          [data-testid="stChatInput"] { border:1px solid var(--ink); border-radius:10px; background:#fcfbf7; }
          .eyebrow { font:600 .72rem 'Manrope', sans-serif; letter-spacing:.15em; text-transform:uppercase; color:var(--muted); }
          .note-card { padding:.6rem 0; border-bottom:1px solid var(--line); font-family:'Manrope', sans-serif; }
          .note-card small { color:var(--muted); }
          .block-container { max-width:1120px; padding-top:3rem; padding-bottom:4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Fieldnotes · Vault RAG", page_icon="◌", layout="wide")
    configure_runtime()
    inject_style()
    settings, container = services()
    if not settings.has_gemini_key:
        st.error("This deployment needs its Gemini API key configured before it can index and search the vault.")
        st.code('GEMINI_API_KEY = "your-key"', language="toml")
        st.stop()
    if settings.generation_provider == "groq" and not settings.has_groq_key:
        st.error("Groq generation is selected, but its API key is missing.")
        st.code('GROQ_API_KEY = "gsk_your-key"', language="toml")
        st.stop()

    try:
        with st.spinner("Preparing your library — indexing field notes…"):
            ensure_index(settings, container)
    except Exception as exc:
        st.error("The vault index could not be prepared. Check the deployment logs and try again.")
        st.exception(exc)
        st.stop()

    notes = source_rows(container)
    total_chunks = container.store.count()

    with st.sidebar:
        st.markdown('<p class="eyebrow">Indexed library</p>', unsafe_allow_html=True)
        st.title("Your field notes")
        st.metric("Searchable notes", len(notes))
        st.caption(f"{total_chunks} passages · semantic retrieval · cited answers")
        st.divider()
        filter_text = st.text_input("Filter notes", placeholder="Filter notes", label_visibility="collapsed")
        for note in notes:
            haystack = f"{note['title']} {note['tags']} {note['rel_path']}".lower()
            if filter_text.lower() not in haystack:
                continue
            st.markdown(
                f'<div class="note-card"><b>{escape(note["title"])}</b> · {note["chunks"]} passages<br>'
                f'<small>{escape(note["tags"] or note["rel_path"])}</small></div>',
                unsafe_allow_html=True,
            )
        st.divider()
        if st.button("Refresh vault index", use_container_width=True):
            try:
                with st.spinner("Re-indexing changed notes…"):
                    ensure_index(settings, container, refresh=True)
                st.success("Vault index is up to date.")
            except Exception as exc:
                st.error(f"Could not refresh the vault: {exc}")

    st.markdown('<p class="eyebrow">Grounded research conversation</p>', unsafe_allow_html=True)
    st.title("Ask your notes. Trace every answer.")
    st.caption("Answers are generated only from retrieved vault passages and include the evidence used.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for source in message.get("sources", []):
                render_source(source)

    question = st.chat_input("Ask a question about your notes…")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    history = [
        {"role": item["role"], "content": item["content"]}
        for item in st.session_state.messages[:-1]
    ]
    with st.chat_message("assistant"):
        with st.spinner("Searching grounded evidence…"):
            try:
                result = container.answer_service.answer(question=question, history=history)
            except RAGError as exc:
                st.error("The answer provider is temporarily busy. Your vault is indexed; please try again shortly.")
                return
            except Exception:
                st.error("The answer service is temporarily unavailable. Please try again shortly.")
                return

        st.markdown(result.answer)
        sources = [asdict(source) for source in result.sources]
        if sources:
            st.caption(f"{len(sources)} cited passage{'s' if len(sources) != 1 else ''}")
            for source in sources:
                render_source(source)
        elif not result.grounded:
            st.caption("No generation was requested because the vault did not provide supporting evidence.")

    st.session_state.messages.append(
        {"role": "assistant", "content": result.answer, "sources": sources}
    )


if __name__ == "__main__":
    main()
