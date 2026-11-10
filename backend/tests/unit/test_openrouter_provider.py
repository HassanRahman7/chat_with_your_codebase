"""OpenRouter provider unit tests (mocked OpenAI client)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    RateLimitError,
)

from app.services.errors import LLMError
from app.services.providers.openrouter import OpenRouterProvider


def _make_provider():
    """Build a provider with a mocked OpenAI client."""
    provider = OpenRouterProvider.__new__(OpenRouterProvider)
    provider._client = MagicMock()
    return provider


def _mock_response(status_code: int) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = {}
    return response


def _mock_completion(text: str):
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def test_openrouter_success(monkeypatch):
    provider = _make_provider()
    provider._client.chat.completions.create.return_value = _mock_completion(
        "The answer is 42."
    )
    result = provider.generate_answer(prompt="What is 2+2?")
    assert result == "The answer is 42."


def test_openrouter_empty_response(monkeypatch):
    provider = _make_provider()
    provider._client.chat.completions.create.return_value = _mock_completion("")
    with pytest.raises(LLMError) as exc:
        provider.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_empty_answer"
    assert exc.value.status_code == 502


def test_openrouter_auth_error(monkeypatch):
    provider = _make_provider()
    exc = AuthenticationError(
        "Invalid API key", response=_mock_response(401), body=None
    )
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_invalid_key"
    assert exc_info.value.status_code == 401


def test_openrouter_model_not_found(monkeypatch):
    provider = _make_provider()
    exc = NotFoundError(
        "Model not found", response=_mock_response(404), body=None
    )
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_model_not_found"
    assert exc_info.value.status_code == 404


def test_openrouter_rate_limit(monkeypatch):
    provider = _make_provider()
    exc = RateLimitError(
        "Rate limited", response=_mock_response(429), body=None
    )
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_rate_limited"
    assert exc_info.value.status_code == 429


def test_openrouter_quota_exhausted(monkeypatch):
    provider = _make_provider()
    exc = RateLimitError(
        "quota exceeded for metric: generate_content_free_tier_requests",
        response=_mock_response(429),
        body="quota exceeded for metric: generate_content_free_tier_requests",
    )
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_quota_exhausted"
    assert exc_info.value.status_code == 429


def test_openrouter_upstream_error(monkeypatch):
    provider = _make_provider()
    exc = APIStatusError(
        "Internal server error",
        response=_mock_response(500),
        body=None,
    )
    exc.status_code = 500
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_upstream_error"
    assert exc_info.value.status_code == 502


def test_openrouter_connection_error_retries(monkeypatch):
    """Transient connection errors are retried with backoff."""
    import time

    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    provider = _make_provider()
    exc = APIConnectionError(
        message="Connection failed", request=MagicMock()
    )
    provider._client.chat.completions.create.side_effect = [
        exc,
        _mock_completion("Success after retry"),
    ]
    result = provider.generate_answer(prompt="Hello")
    assert result == "Success after retry"
    assert len(sleeps) == 1  # One retry with backoff


def test_openrouter_timeout_retries(monkeypatch):
    """Transient timeouts are retried with backoff."""
    import time

    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    provider = _make_provider()
    exc = APITimeoutError(request=MagicMock())
    provider._client.chat.completions.create.side_effect = [
        exc,
        _mock_completion("Success after retry"),
    ]
    result = provider.generate_answer(prompt="Hello")
    assert result == "Success after retry"
    assert len(sleeps) == 1


def test_openrouter_no_api_key(monkeypatch):
    """Missing API key raises LLMError at request time."""
    monkeypatch.setattr("app.config.settings.openrouter_api_key", None)
    provider = OpenRouterProvider.__new__(OpenRouterProvider)
    provider._client = None
    with pytest.raises(LLMError) as exc:
        provider.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_not_configured"
    assert exc.value.status_code == 503


def test_openrouter_bad_request(monkeypatch):
    """400 BadRequestError is not retried."""
    provider = _make_provider()
    exc = BadRequestError(
        "Malformed request", response=_mock_response(400), body=None
    )
    provider._client.chat.completions.create.side_effect = exc
    with pytest.raises(LLMError) as exc_info:
        provider.generate_answer(prompt="Hello")
    assert exc_info.value.code == "llm_bad_request"
    assert exc_info.value.status_code == 400
