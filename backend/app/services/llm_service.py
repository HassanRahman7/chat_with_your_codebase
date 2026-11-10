"""LLM provider dispatcher.

Selects the active language model provider via ``settings.llm_provider``
(``gemini`` or ``openrouter``) and delegates ``generate_answer`` to it.
The RAG pipeline calls this module without knowing which provider is active.

No API key or secret is logged or returned to the client.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.services.errors import LLMError
from app.services.providers.gemini import GeminiProvider
from app.services.providers.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


# Module-level provider instances, created lazily on first use.
_gemini_provider: GeminiProvider | None = None
_openrouter_provider: OpenRouterProvider | None = None


def _get_provider():
    """Return the provider instance for ``settings.llm_provider``."""
    provider_name = settings.llm_provider or "gemini"

    if provider_name == "openrouter":
        global _openrouter_provider
        if _openrouter_provider is None:
            _openrouter_provider = OpenRouterProvider()
        return _openrouter_provider

    # Default: Gemini (preserves existing behaviour).
    global _gemini_provider
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
    return _gemini_provider


def generate_answer(
    *,
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
) -> str:
    """Send a prompt to the active language model and return the raw text.

    Delegates to the provider selected by ``settings.llm_provider``.
    """
    provider = _get_provider()
    return provider.generate_answer(
        prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
