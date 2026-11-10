"""Gemini LLM client via the REST API.

Uses ``httpx`` (already a core dependency) to call the Gemini
``generateContent`` endpoint. Keeps the provider behind a service interface so
it can be replaced without touching routers or RAG logic.

No API key or secret is logged or returned to the client.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings
from app.services.errors import LLMError

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.gemini_api_key or "",
    }


def _model_url() -> str:
    return f"{_GEMINI_BASE}/models/{settings.gemini_model}:generateContent"


def generate_answer(
    *,
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
) -> str:
    """Send a prompt to Gemini and return the raw text response."""
    if not settings.gemini_api_key:
        raise LLMError(
            "Gemini API key is not configured.", code="llm_not_configured", status_code=503
        )

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(_model_url(), headers=_headers(), json=payload)
    except httpx.TimeoutException as exc:
        logger.warning("Gemini request timed out: %s", exc)
        raise LLMError(
            "The language model request timed out.",
            code="llm_timeout",
            status_code=504,
        ) from exc
    except httpx.RequestError as exc:  # noqa: BLE001
        logger.warning("Gemini request failed: %s", type(exc).__name__)
        raise LLMError(
            "The language model service is unavailable.",
            code="llm_unavailable",
            status_code=502,
        ) from exc

    if response.status_code >= 400:
        logger.warning(
            "Gemini returned HTTP %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise LLMError(
            "The language model returned an error.",
            code="llm_upstream_error",
            status_code=502,
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:  # noqa: BLE001
        logger.warning("Gemini returned invalid JSON: %s", response.text[:500])
        raise LLMError(
            "The language model returned an invalid response.",
            code="llm_invalid_response",
            status_code=502,
        ) from exc

    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Gemini response missing content: %s", data)
        raise LLMError(
            "The language model returned no content.",
            code="llm_no_content",
            status_code=502,
        ) from exc

    if not text or not text.strip():
        raise LLMError(
            "The language model returned an empty answer.",
            code="llm_empty_answer",
            status_code=502,
        )

    return text.strip()
