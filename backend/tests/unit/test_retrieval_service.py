"""Retrieval service unit tests."""

from __future__ import annotations

import uuid

from app.services import retrieval_service
from app.services.retrieval_service import RetrievedChunk, source_map


def _chunk(*, source_id="source-1", score=0.9):
    return RetrievedChunk(
        source_id=source_id,
        chunk_id="chunk-uuid",
        repository_id="repo-uuid",
        index_version="index-uuid",
        file_path="src/auth/service.py",
        symbol_name="authenticate_user",
        parent_symbol=None,
        start_line=12,
        end_line=34,
        content="def authenticate_user(username, password):\n    return True",
        content_hash="hash",
        chunk_strategy="syntax",
        complete=True,
        partial=False,
        score=score,
    )


def test_make_source_id_is_sequential() -> None:
    assert retrieval_service._make_source_id(0) == "source-1"
    assert retrieval_service._make_source_id(1) == "source-2"
    assert retrieval_service._make_source_id(4) == "source-5"


def test_source_map_lookup() -> None:
    chunks = [_chunk(source_id="source-1"), _chunk(source_id="source-2")]
    smap = source_map(chunks)
    assert set(smap.keys()) == {"source-1", "source-2"}
    assert smap["source-1"].file_path == "src/auth/service.py"


def test_build_context_includes_source_ids_and_locations() -> None:
    chunks = [_chunk(source_id="source-1")]
    context = retrieval_service.build_context(chunks)
    assert "[source-1]" in context
    assert "src/auth/service.py" in context
    assert "L12-34" in context
    assert "authenticate_user" in context
    assert "def authenticate_user" in context
