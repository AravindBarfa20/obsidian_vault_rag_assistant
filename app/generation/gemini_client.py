"""Thin Gemini generation client (Gemini Flash).

Isolated behind a small surface so generation is swappable and testable. It is
only responsible for turning (system prompt, user prompt) into text; retrieval
and grounding decisions happen upstream.
"""

from __future__ import annotations

from app.core.exceptions import ConfigurationError, GenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
    ) -> None:
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is required for generation.")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=self._temperature,
                    max_output_tokens=self._max_output_tokens,
                    # This RAG client does not expose tools. Disabling AFC
                    # avoids SDK warnings and keeps generation deterministic.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )
        except Exception as exc:
            logger.exception("Gemini generation failed")
            raise GenerationError(f"LLM call failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise GenerationError("LLM returned an empty response.")
        return text
