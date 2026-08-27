"""Answer service: the RAG orchestration seam.

    condense (if follow-up) -> retrieve -> gate -> generate -> attach sources

Enforces the no-answer contract in code: when retrieval finds no grounding, it
returns the fallback message WITHOUT calling the LLM, so hallucination is
structurally impossible on empty retrieval rather than merely discouraged by
the prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger
from app.generation.llm_factory import LLM
from app.generation.prompt import (
    CONDENSE_PROMPT,
    NO_CONTEXT_MESSAGE,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.models.documents import RetrievedChunk
from app.retrieval.retriever import Retriever

logger = get_logger(__name__)


@dataclass
class Source:
    source: str
    title: str
    section: str
    path: str
    relevance: float
    snippet: str


@dataclass
class Answer:
    answer: str
    sources: list[Source]
    grounded: bool
    query_used: str  # the (possibly condensed) query actually searched
    model: str


def _to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    return [
        Source(
            source=c.source,
            title=c.title,
            section=c.section,
            path=c.rel_path,
            relevance=round(c.relevance, 4),
            snippet=c.text[:280] + ("…" if len(c.text) > 280 else ""),
        )
        for c in chunks
    ]


class AnswerService:
    def __init__(self, retriever: Retriever, llm: LLM, settings: Settings) -> None:
        self._retriever = retriever
        self._llm = llm
        self._settings = settings

    def _condense(self, question: str, history: list[dict[str, str]]) -> str:
        """Rewrite a follow-up into a standalone query using recent history."""
        if not history or not self._settings.enable_query_condensation:
            return question
        turns = history[-self._settings.max_history_turns :]
        rendered = "\n".join(f"{t.get('role', 'user')}: {t.get('content', '')}" for t in turns)
        try:
            standalone = self._llm.generate(
                system_prompt="You rewrite follow-up questions to be standalone.",
                user_prompt=CONDENSE_PROMPT.format(history=rendered, question=question),
            ).strip()
            return standalone or question
        except Exception:  # condensation is best-effort; fall back to raw question
            logger.warning("Query condensation failed; using original question.")
            return question

    def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        top_k: int | None = None,
        threshold: float | None = None,
        tag: str | None = None,
    ) -> Answer:
        search_query = self._condense(question, history or [])
        result = self._retriever.retrieve(
            search_query, top_k=top_k, threshold=threshold, tag=tag
        )

        # No-answer gate: without grounding we never call the generator.
        if not result.has_grounding:
            logger.info("No grounding for query; returning no-answer response.")
            return Answer(
                answer=NO_CONTEXT_MESSAGE,
                sources=[],
                grounded=False,
                query_used=search_query,
                model=self._llm.model_name,
            )

        user_prompt = build_user_prompt(question, result.chunks)
        answer_text = self._llm.generate(SYSTEM_PROMPT, user_prompt)
        return Answer(
            answer=answer_text,
            sources=_to_sources(result.chunks),
            grounded=True,
            query_used=search_query,
            model=self._llm.model_name,
        )
