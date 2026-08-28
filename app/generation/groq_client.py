"""Thin Groq generation client for grounded RAG answers.

Embeddings remain provider-independent. This client only turns the already
retrieved evidence and system prompt into an answer, matching the small LLM
surface used by the rest of the application.
"""

from __future__ import annotations

from app.core.exceptions import ConfigurationError, GenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


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
            text = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.exception("Groq generation failed")
            raise GenerationError(f"LLM call failed: {exc}") from exc

        if not text:
            raise GenerationError("Groq returned an empty response.")
        return text
