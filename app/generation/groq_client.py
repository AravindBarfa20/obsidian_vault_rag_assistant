"""Thin Groq generation client for grounded RAG answers.

Embeddings remain provider-independent. This client only turns the already
retrieved evidence and system prompt into an answer, matching the small LLM
surface used by the rest of the application.
"""

from __future__ import annotations

import re

from app.core.exceptions import ConfigurationError, GenerationError
from app.core.logging import get_logger
from app.generation.output_cleaner import clean_answer_text

logger = get_logger(__name__)

_THINKING_BLOCK = re.compile(r"<think>.*?</think>\s*", re.IGNORECASE | re.DOTALL)


def _final_answer(raw_text: str) -> str:
    """Drop provider reasoning traces; only a user-facing final answer may leave.

    Some reasoning-capable Groq models include an XML-like ``<think>`` block in
    ordinary completion text. That is implementation detail, not cited vault
    evidence, and must never appear in the assistant UI.
    """
    text = clean_answer_text(_THINKING_BLOCK.sub("", raw_text))
    if text.lower().startswith("<think>"):
        # An unclosed block usually means generation stopped before the model
        # reached its answer. Do not present an incomplete private trace.
        return ""
    return text


class GroqClient:
    def __init__(
        self,
        api_key: str,
        model_name: str = "qwen/qwen3.6-27b",
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
    ) -> None:
        if not api_key:
            raise ConfigurationError("GROQ_API_KEY is required for Groq generation.")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_completion_tokens=self._max_output_tokens,
            )
            text = _final_answer(response.choices[0].message.content or "")
        except Exception as exc:
            logger.exception("Groq generation failed")
            raise GenerationError(f"LLM call failed: {exc}") from exc

        if not text:
            raise GenerationError("Groq returned an empty response.")
        return text
