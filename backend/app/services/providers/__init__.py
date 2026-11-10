"""LLM provider implementations.

Exposes a common ``generate_answer`` interface so the RAG pipeline stays
provider-agnostic. The active provider is selected via ``settings.llm_provider``.
"""

from __future__ import annotations

from app.services.providers.base import LLMProvider

__all__ = ["LLMProvider"]
