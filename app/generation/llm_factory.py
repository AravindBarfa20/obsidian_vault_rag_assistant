"""Select a generation LLM from configuration (Gemini, else offline FakeLLM)."""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLM(Protocol):
    @property
    def model_name(self) -> str: ...

    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


def build_llm(settings: Settings) -> LLM:
    if settings.has_gemini_key:
        from app.generation.gemini_client import GeminiClient

        logger.info("Using Gemini LLM: %s", settings.llm_model)
        return GeminiClient(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )

    from app.generation.fake_llm import FakeLLM

    logger.warning("No GEMINI_API_KEY set -> using FakeLLM (offline mode).")
    return FakeLLM()
