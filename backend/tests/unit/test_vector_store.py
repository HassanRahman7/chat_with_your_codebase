"""Vector store service unit tests."""

from __future__ import annotations

import uuid

import pytest

from app.config import settings
from app.database.vector_db import reset_chroma_client
from app.services.chunking_service import CodeChunk
from app.services import vector_store_service


@pytest.fixture()
def temp_chroma_dir(tmp_path, monkeypatch):
    """Use a temporary ChromaDB directory and reset the cached client."""
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(settings, "chroma_persist_directory", chroma_dir)
    reset_chroma_client()
    yield chroma_dir
    reset_chroma_client()


def _make_chunk(repository_id, index_version, chunk_id, content, file_path="src/x.py"):
    return CodeChunk(
        chunk_id=chunk_id,
        repository_id=repository_id,
        commit_sha="abc123",
        file_path=file_path,
        language="python",
        chunk_type="function",
        symbol_name="foo",
        parent_symbol=None,
        start_line=1,
        end_line=3,
        content=content,
        content_hash="hash",
        chunk_strategy="syntax",
        complete=True,
        partial=False,
    )


def test_upsert_and_query_chunks(temp_chroma_dir):
    repository_id = uuid.uuid4()
    index_version = uuid.uuid4()

    chunks = [
        _make_chunk(repository_id, index_version, str(uuid.uuid4()), "def add(a, b):\n    return a + b\n"),
        _make_chunk(repository_id, index_version, str(uuid.uuid4()), "def sub(a, b):\n    return a - b\n"),
    ]
    embeddings = [[0.1] * 384, [0.2] * 384]

    vector_store_service.upsert_chunks(repository_id, index_version, chunks, embeddings)

    assert vector_store_service.count_chunks(repository_id, index_version) == 2
    assert vector_store_service.count_chunks(repository_id) == 2

    results = vector_store_service.query_chunks(
        repository_id, index_version, [0.1] * 384, top_k=5
    )
    assert len(results) == 2
    assert all(r.repository_id == str(repository_id) for r in results)
    assert all(r.index_version == str(index_version) for r in results)
    assert all(r.score is not None and 0.0 <= r.score <= 1.0 for r in results)


def test_query_filters_by_index_version(temp_chroma_dir):
    repository_id = uuid.uuid4()
    index_v1 = uuid.uuid4()
    index_v2 = uuid.uuid4()

    chunks_v1 = [_make_chunk(repository_id, index_v1, str(uuid.uuid4()), "v1 content\n")]
    chunks_v2 = [_make_chunk(repository_id, index_v2, str(uuid.uuid4()), "v2 content\n")]

    vector_store_service.upsert_chunks(repository_id, index_v1, chunks_v1, [[0.5] * 384])
    vector_store_service.upsert_chunks(repository_id, index_v2, chunks_v2, [[0.5] * 384])

    assert vector_store_service.count_chunks(repository_id) == 2
    assert vector_store_service.count_chunks(repository_id, index_v1) == 1
    assert vector_store_service.count_chunks(repository_id, index_v2) == 1

    results = vector_store_service.query_chunks(
        repository_id, index_v1, [0.5] * 384, top_k=5
    )
    assert len(results) == 1
    assert results[0].content == "v1 content\n"


def test_delete_repository_index(temp_chroma_dir):
    repository_id = uuid.uuid4()
    index_version = uuid.uuid4()

    chunks = [_make_chunk(repository_id, index_version, str(uuid.uuid4()), "content\n")]
    vector_store_service.upsert_chunks(repository_id, index_version, chunks, [[0.5] * 384])

    assert vector_store_service.count_chunks(repository_id, index_version) == 1

    vector_store_service.delete_repository_index(repository_id, index_version)
    assert vector_store_service.count_chunks(repository_id, index_version) == 0


def test_query_unknown_repository_returns_empty(temp_chroma_dir):
    results = vector_store_service.query_chunks(
        uuid.uuid4(), uuid.uuid4(), [0.1] * 384, top_k=5
    )
    assert results == []
