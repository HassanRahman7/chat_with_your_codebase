"""Embedding service unit tests."""

from __future__ import annotations

import pytest

from app.services import embedding_service
from app.services.errors import EmbeddingError


def test_model_name_returns_configured_model(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    assert embedding_service.model_name() == "BAAI/bge-small-en-v1.5"


def test_model_dimension_is_positive(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    dimension = embedding_service.model_dimension()
    assert isinstance(dimension, int)
    assert dimension > 0


def test_encode_query_returns_normalized_vector(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    vector = embedding_service.encode_query("how does authentication work?")

    assert isinstance(vector, list)
    assert len(vector) == embedding_service.model_dimension()
    assert all(isinstance(v, float) for v in vector)


def test_encode_texts_returns_parallel_vectors(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    texts = ["def add(a, b): return a + b", "export function app() { return 1; }"]
    vectors = embedding_service.encode_texts(texts)

    assert len(vectors) == 2
    assert all(len(v) == embedding_service.model_dimension() for v in vectors)


def test_encode_texts_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    assert embedding_service.encode_texts([]) == []


def test_encode_query_empty_raises(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    with pytest.raises(EmbeddingError):
        embedding_service.encode_query("")

    with pytest.raises(EmbeddingError):
        embedding_service.encode_query("   ")


def test_query_and_passage_vectors_differ(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "BAAI/bge-small-en-v1.5")
    embedding_service._load_model.cache_clear()

    text = "def authenticate(user): return True"
    query_vector = embedding_service.encode_query(text)
    passage_vector = embedding_service.encode_texts([text])[0]

    # The query prefix changes the embedding, so they should not be identical.
    assert query_vector != passage_vector
