"""LLM service unit tests (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services import llm_service
from app.services.errors import LLMError


def _mock_response(status_code=200, json_body=None, text=""):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    if json_body is not None:
        response.json.return_value = json_body
    else:
        response.json.return_value = {}
    response.text = text
    return response


def test_generate_answer_success(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "llm_provider", "gemini")
    monkeypatch.setattr(
        llm_service.settings, "gemini_api_key", "test-key-12345"
    )
    monkeypatch.setattr(llm_service.settings, "llm_timeout_seconds", 60)

    mock_client = MagicMock()
    mock_response = _mock_response(
        json_body={
            "candidates": [
                {"content": {"parts": [{"text": "The answer is 42."}]}}
            ]
        }
    )
    mock_client.__enter__.return_value.post.return_value = mock_response

    # GeminiProvider uses httpx.Client internally.
    with patch("app.services.providers.gemini.httpx.Client", return_value=mock_client):
        result = llm_service.generate_answer(prompt="What is the answer?")
    assert result == "The answer is 42."


def test_generate_answer_no_api_key(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "llm_provider", "gemini")
    monkeypatch.setattr(llm_service.settings, "gemini_api_key", None)
    with pytest.raises(LLMError) as exc:
        llm_service.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_not_configured"
    assert exc.value.status_code == 503


def test_generate_answer_timeout(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "llm_provider", "gemini")
    monkeypatch.setattr(
        llm_service.settings, "gemini_api_key", "test-key-12345"
    )
    monkeypatch.setattr(llm_service.settings, "llm_timeout_seconds", 60)

    mock_client = MagicMock()
    mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException(
        "timeout"
    )

    with patch("app.services.providers.gemini.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError) as exc:
            llm_service.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_timeout"
    assert exc.value.status_code == 504


def test_generate_answer_http_error(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "llm_provider", "gemini")
    monkeypatch.setattr(
        llm_service.settings, "gemini_api_key", "test-key-12345"
    )
    monkeypatch.setattr(llm_service.settings, "llm_timeout_seconds", 60)

    mock_client = MagicMock()
    mock_response = _mock_response(status_code=500, text="Internal error")
    mock_client.__enter__.return_value.post.return_value = mock_response

    with patch("app.services.providers.gemini.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError) as exc:
            llm_service.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_upstream_error"
    assert exc.value.status_code == 502


def test_generate_answer_openrouter_not_configured(monkeypatch):
    """OpenRouter without an API key raises LLMError."""
    monkeypatch.setattr(llm_service.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm_service.settings, "openrouter_api_key", None)

    # Force a fresh provider instance since it's cached at module level.
    llm_service._openrouter_provider = None

    with pytest.raises(LLMError) as exc:
        llm_service.generate_answer(prompt="Hello")
    assert exc.value.code == "llm_not_configured"
    assert exc.value.status_code == 503
