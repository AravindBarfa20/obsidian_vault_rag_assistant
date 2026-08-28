"""Prompt construction for grounded generation.

The context is presented as numbered, labelled sources ([S1], [S2], ...). The
model is told to ground every claim in these sources, cite them inline, and to
decline when the sources are insufficient -- the vault is the source of truth,
not the model's parametric memory.
"""

from __future__ import annotations

from app.models.documents import RetrievedChunk

SYSTEM_PROMPT = """You are a knowledge assistant that answers questions strictly \
from a user's personal Obsidian notes.

Rules you must follow:
1. Use ONLY the information in the provided SOURCES. Do not use outside \
knowledge or assumptions.
2. Ground every factual claim in the sources and cite them inline using their \
labels, e.g. [S1] or [S2][S3].
3. If the sources do not contain enough information to answer, reply with \
exactly: "I couldn't find enough information about this in your Obsidian \
vault." Do not guess or fabricate.
4. Distinguish clearly between what the notes state and any gaps. If the notes \
only partially answer, say what is supported and what is missing.
5. Answer in natural prose. Do not dump raw note text; synthesise it.
6. Be concise and specific. Prefer the user's own terminology from the notes.
7. Return only the final answer for the user. Never include analysis, reasoning
steps, or tags such as <think>.
"""

NO_CONTEXT_MESSAGE = (
    "I couldn't find enough information about this in your Obsidian vault."
)


def format_sources(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as labelled sources for the prompt."""
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        location = chunk.source
        if chunk.section:
            location += f" > {chunk.section}"
        blocks.append(
            f"[S{index}] (note: {location})\n{chunk.text.strip()}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    sources = format_sources(chunks)
    return (
        f"SOURCES:\n{sources}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the sources above, citing them inline as [S#]. "
        "If they are insufficient, use the exact fallback sentence."
    )


CONDENSE_PROMPT = """Given a conversation and a follow-up question, rewrite the \
follow-up as a standalone question that includes any context needed to search a \
knowledge base. Return ONLY the rewritten question, nothing else.

Conversation:
{history}

Follow-up question: {question}

Standalone question:"""
