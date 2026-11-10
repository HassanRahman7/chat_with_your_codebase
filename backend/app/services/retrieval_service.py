"""Repository-scoped semantic retrieval.

Normalizes ChromaDB results into application-level retrieval records and
generates backend-owned ``source_id`` values that the LLM is allowed to cite.
The retrieval service never trusts client-supplied source identifiers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.services.vector_store_service import ChunkRecord, query_chunks


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieval result safe to expose to the LLM as citation context."""

    source_id: str
    chunk_id: str
    repository_id: str
    index_version: str
    file_path: str
    symbol_name: str | None
    parent_symbol: str | None
    start_line: int
    end_line: int
    content: str
    content_hash: str
    chunk_strategy: str
    complete: bool
    partial: bool
    score: float


def _make_source_id(index: int) -> str:
    """Generate a backend-owned source ID for a retrieved chunk.

    Only these IDs are valid citation targets for the current answer context.
    """
    return f"source-{index + 1}"


def retrieve(
    *,
    repository_id: str | uuid.UUID,
    index_version: str | uuid.UUID,
    query_embedding: list[float],
    top_k: int | None = None,
    min_relevance: float | None = None,
) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for a repository + active index.

    Every query is filtered by the exact ``repository_id`` and
    ``index_version``. Results are ranked by ChromaDB similarity and returned
    with backend-generated source IDs.
    """
    top_k = settings.retrieval_top_k if top_k is None else top_k
    min_relevance = (
        settings.retrieval_min_relevance
        if min_relevance is None
        else min_relevance
    )

    records = query_chunks(
        repository_id=str(repository_id),
        index_version=str(index_version),
        query_embedding=query_embedding,
        top_k=top_k,
        min_relevance=min_relevance,
    )

    chunks: list[RetrievedChunk] = []
    for index, record in enumerate(records):
        chunks.append(
            RetrievedChunk(
                source_id=_make_source_id(index),
                chunk_id=record.chunk_id,
                repository_id=record.repository_id,
                index_version=record.index_version,
                file_path=record.file_path,
                symbol_name=record.symbol_name,
                parent_symbol=record.parent_symbol,
                start_line=record.start_line,
                end_line=record.end_line,
                content=record.content,
                content_hash=record.content_hash,
                chunk_strategy=record.chunk_strategy,
                complete=record.complete,
                partial=record.partial,
                score=record.score,
            )
        )
    return chunks


def source_map(chunks: list[RetrievedChunk]) -> dict[str, RetrievedChunk]:
    """Return a lookup of source_id -> RetrievedChunk for citation validation."""
    return {chunk.source_id: chunk for chunk in chunks}


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Build bounded, source-labelled context text for the LLM prompt.

    Context lines are drawn only from trusted retrieval records. The LLM is
    instructed to cite by source_id only.
    """
    blocks: list[str] = []
    for chunk in chunks:
        location = chunk.file_path
        if chunk.symbol_name:
            location = f"{location} ({chunk.symbol_name})"
        location += f" L{chunk.start_line}-{chunk.end_line}"
        blocks.append(
            f"[{chunk.source_id}] {location}\n{chunk.content}"
        )
    return "\n\n---\n\n".join(blocks)
