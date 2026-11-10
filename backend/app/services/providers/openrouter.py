"""OpenRouter LLM provider via the OpenAI-compatible chat completions API.

Routes requests to NVIDIA Nemotron 3 Ultra (and other models) through
OpenRouter's OpenAI-compatible endpoint. Implements the same
``LLMProvider`` interface as the Gemini provider.

No API key or secret is logged or returned to the client.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletion

from app.config import settings
from app.services.errors import LLMError

logger = logging.getLogger(__name__)

# Transient status codes worth retrying (5xx + 429 retry-after).
_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_INITIAL_BACKOFF_SECONDS = 1.0


class OpenRouterProvider:
    """OpenRouter provider implementation using the OpenAI Python SDK."""

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            # Defer the error to generate_answer so configuration issues
            # surface at request time, not import time.
            self._client: OpenAI | None = None
        else:
            self._client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )

    def generate_answer(
        self,
        *,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> str:
        """Send a prompt to Nemotron via OpenRouter and return the raw text."""
        if self._client is None:
            raise LLMError(
                "OpenRouter API key is not configured.",
                code="llm_not_configured",
                status_code=503,
            )

        last_error: Exception | None = None
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES + 1):
            try:
                completion: ChatCompletion = self._client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful codebase assistant. "
                                "Answer using only the provided context. "
                                "Do not invent file paths or line numbers."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    # OpenRouter-specific headers for attribution (optional).
                    extra_headers=self._extra_headers(),
                )
                return self._extract_text(completion)

            except AuthenticationError as exc:
                # 401: invalid or missing API key — never retry.
                logger.warning("OpenRouter authentication failed: %s", type(exc).__name__)
                raise LLMError(
                    "Invalid OpenRouter API key.",
                    code="llm_invalid_key",
                    status_code=401,
                ) from exc

            except BadRequestError as exc:
                # 400: malformed request — never retry.
                logger.warning("OpenRouter bad request: %s", exc)
                raise LLMError(
                    "The request to the language model was malformed.",
                    code="llm_bad_request",
                    status_code=400,
                ) from exc

            except RateLimitError as exc:
                # 429: rate limit or quota exhausted — never retry for quota.
                # Distinguish via the provider's error message when possible.
                body = self._extract_error_body(exc)
                is_quota = "quota" in body.lower() or "daily" in body.lower()
                code = "llm_quota_exhausted" if is_quota else "llm_rate_limited"
                message = (
                    "The OpenRouter free model quota has been exhausted. "
                    "Please try again later or upgrade your plan."
                    if is_quota
                    else "The language model is rate-limited. Please try again shortly."
                )
                logger.warning(
                    "OpenRouter rate limited (quota=%s): %s", is_quota, exc
                )
                raise LLMError(message, code=code, status_code=429) from exc

            except NotFoundError as exc:
                # 404: model not found — never retry.
                logger.warning("OpenRouter model not found: %s", exc)
                raise LLMError(
                    "The requested language model is not available.",
                    code="llm_model_not_found",
                    status_code=404,
                ) from exc

            except (APIConnectionError, APITimeoutError) as exc:
                # Transient network/upstream issues — retry with backoff.
                last_error = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "OpenRouter transient error (attempt %d/%d): %s",
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        type(exc).__name__,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                logger.warning(
                    "OpenRouter request failed after retries: %s", type(exc).__name__
                )
                raise LLMError(
                    "The language model service is unavailable.",
                    code="llm_unavailable",
                    status_code=502,
                ) from exc

            except APIStatusError as exc:
                # Other HTTP status codes.
                if exc.status_code in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES:
                    last_error = exc
                    logger.warning(
                        "OpenRouter upstream error %d (attempt %d/%d): %s",
                        exc.status_code,
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        exc,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                logger.warning(
                    "OpenRouter returned HTTP %s: %s", exc.status_code, exc
                )
                raise LLMError(
                    "The language model returned an error.",
                    code="llm_upstream_error",
                    status_code=502,
                ) from exc

            except Exception as exc:  # noqa: BLE001 - unexpected provider failure
                # Let LLMError (e.g. empty answer from _extract_text) propagate.
                if isinstance(exc, LLMError):
                    raise
                logger.warning(
                    "OpenRouter unexpected error: %s", type(exc).__name__
                )
                raise LLMError(
                    "The language model service is unavailable.",
                    code="llm_unavailable",
                    status_code=502,
                ) from exc

        # Should not be reached (loop either returns or raises), but satisfy
        # type checkers.
        raise LLMError(
            "The language model service is unavailable.",
            code="llm_unavailable",
            status_code=502,
        ) from last_error

    @staticmethod
    def _extract_text(completion: ChatCompletion) -> str:
        """Extract the assistant's text content from a completion."""
        try:
            message = completion.choices[0].message
            text = message.content or ""
        except (IndexError, AttributeError) as exc:
            logger.warning("OpenRouter response missing content: %s", completion)
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

    @staticmethod
    def _extract_error_body(exc: Exception) -> str:
        """Best-effort extraction of the provider error body for classification."""
        try:
            body = str(exc)
            return body
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _extra_headers() -> dict[str, str]:
        """Optional OpenRouter attribution headers (never contains secrets)."""
        headers: dict[str, str] = {}
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        return headers
