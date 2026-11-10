"""Abstract base class for LLM providers.

Every provider must implement ``generate_answer`` with the same signature so the
RAG pipeline can call it without knowing which provider is active.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface for language model providers."""

    @abstractmethod
    def generate_answer(
        self,
        *,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> str:
        """Send a prompt to the model and return the raw text response.

        Raises ``LLMError`` (or a subclass) on provider failures.
        """
        raise NotImplementedError
