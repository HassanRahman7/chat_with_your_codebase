"""RAG service citation validation unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services import rag_service
from app.services.errors import LLMError
from app.services.retrieval_service import RetrievedChunk, source_map


def _chunk(*, source_id, file_path="src/auth/service.py", symbol_name="authenticate_user", start_line=12, end_line=34, content="def authenticate_user(username, password):\n    return True"):
    return RetrievedChunk(
        source_id=source_id,
        chunk_id="chunk-uuid",
        repository_id="repo-uuid",
        index_version="index-uuid",
        file_path=file_path,
        symbol_name=symbol_name,
        parent_symbol=None,
        start_line=start_line,
        end_line=end_line,
        content=content,
        content_hash="hash",
        chunk_strategy="syntax",
        complete=True,
        partial=False,
        score=0.9,
    )


def _repository():
    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.active_index_version = uuid.uuid4()
    repo.active_commit_sha = "abc123def456"
    return repo


def test_validate_citations_accepts_valid_source_ids() -> None:
    chunks = [_chunk(source_id="source-1"), _chunk(source_id="source-2")]
    smap = source_map(chunks)
    parsed = {
        "answer": "Auth is in the auth service.",
        "citations": [
            {"source_id": "source-1", "claim": "Auth is handled here."},
            {"source_id": "source-2", "claim": "Also here."},
        ],
        "insufficient_evidence": False,
    }
    citations = rag_service._validate_citations(
        parsed=parsed, source_map=smap, commit_sha="abc123"
    )
    assert len(citations) == 2
    assert citations[0].source_id == "source-1"
    assert citations[0].file_path == "src/auth/service.py"
    assert citations[0].symbol_name == "authenticate_user"
    assert citations[0].start_line == 12
    assert citations[0].end_line == 34
    assert citations[0].commit_sha == "abc123"
    assert citations[0].snippet == "def authenticate_user(username, password):\n    return True"


def test_validate_citations_omits_unknown_source_ids() -> None:
    chunks = [_chunk(source_id="source-1")]
    smap = source_map(chunks)
    parsed = {
        "answer": "Answer.",
        "citations": [
            {"source_id": "source-1", "claim": "Valid."},
            {"source_id": "source-99", "claim": "Invalid."},
        ],
        "insufficient_evidence": False,
    }
    citations = rag_service._validate_citations(
        parsed=parsed, source_map=smap, commit_sha="abc123"
    )
    assert len(citations) == 1
    assert citations[0].source_id == "source-1"


def test_validate_citations_deduplicates() -> None:
    chunks = [_chunk(source_id="source-1")]
    smap = source_map(chunks)
    parsed = {
        "answer": "Answer.",
        "citations": [
            {"source_id": "source-1", "claim": "First."},
            {"source_id": "source-1", "claim": "Duplicate."},
        ],
        "insufficient_evidence": False,
    }
    citations = rag_service._validate_citations(
        parsed=parsed, source_map=smap, commit_sha="abc123"
    )
    assert len(citations) == 1


def test_parse_structured_output_valid() -> None:
    text = '{"answer": "Hello", "citations": [], "insufficient_evidence": false}'
    parsed = rag_service._parse_structured_output(text)
    assert parsed["answer"] == "Hello"
    assert parsed["citations"] == []
    assert parsed["insufficient_evidence"] is False


def test_parse_structured_output_strips_markdown_fences() -> None:
    text = "```json\n{\"answer\": \"Hello\", \"citations\": [], \"insufficient_evidence\": false}\n```"
    parsed = rag_service._parse_structured_output(text)
    assert parsed["answer"] == "Hello"


def test_parse_structured_output_invalid_raises() -> None:
    """Invalid JSON that also fails the repair path raises LLMError."""
    # Mock generate_answer to return invalid JSON, so the repair path fails too.
    with patch(
        "app.services.rag_service.generate_answer",
        return_value="not valid json either",
    ):
        with pytest.raises(LLMError):
            rag_service._parse_structured_output("not json at all")

    with patch(
        "app.services.rag_service.generate_answer",
        return_value='{"answer": 123, "citations": [], "insufficient_evidence": false}',
    ):
        with pytest.raises(LLMError):
            rag_service._parse_structured_output("not json at all")

    with patch(
        "app.services.rag_service.generate_answer",
        return_value='{"answer": "Hi", "citations": [], "insufficient_evidence": "yes"}',
    ):
        with pytest.raises(LLMError):
            rag_service._parse_structured_output("not json at all")
