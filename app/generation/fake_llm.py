"""Deterministic stand-in LLM for offline dev and tests.

It does not reason; it produces a grounded-looking answer from the retrieved
sources (or the exact fallback sentence when there are none), so the full
pipeline -- including no-answer behaviour and citations -- is exercisable
without an API key.
"""

from __future__ import annotations

from app.generation.prompt import NO_CONTEXT_MESSAGE


class FakeLLM:
    model_name = "fake-llm"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Query-condensation prompt: the fake LLM cannot rewrite, so it returns
        # the follow-up unchanged (honest offline behaviour) rather than echoing
        # a canned answer as the search query.
        if "Standalone question:" in user_prompt and "Follow-up question:" in user_prompt:
            after = user_prompt.split("Follow-up question:", 1)[1]
            return after.split("Standalone question:", 1)[0].strip()
        if "SOURCES:\n\n" in user_prompt or "SOURCES:\n\nQUESTION" in user_prompt:
            return NO_CONTEXT_MESSAGE
        # Echo a short grounded answer citing the first source.
        return (
            "Based on your notes, here is what is supported by the retrieved "
            "context [S1]. (This is a deterministic offline response; configure "
            "GEMINI_API_KEY for real generation.)"
        )
