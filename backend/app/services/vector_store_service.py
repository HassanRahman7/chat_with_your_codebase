"""ChromaDB vector store service.

Owns all ChromaDB operations: upsert code chunks, query chunks filtered by
repository and active index version, and retire/delete index versions. ChromaDB
details stay out of routers and RAG prompt code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.database.vector_db import get_chroma_client
from app.services.errors import VectorStoreError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    content: str
    repository_id: str
    commit_sha: str
    index_version: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None
    parent_symbol: str | None
    start_line: int
    end_line: int
    content_hash: str
    chunk_strategy: str
    complete: bool
    partial: bool
    score: float | None = None


def _collection():
    """Return (and lazily create) the shared code-chunks collection."""
    client = get_chroma_client()
    try:
        return client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception("Could not open ChromaDB collection %s", settings.chroma_collection_name)
        raise VectorStoreError(
            "ChromaDB collection could not be opened."
        ) from exc


def _where(repository_id, index_version: str | None = None) -> dict[str, Any]:
    """Build a ChromaDB where filter (single condition or $and for multiple)."""
    conditions = [{"repository_id": str(repository_id)}]
    if index_version is not None:
        conditions.append({"index_version": str(index_version)})
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _metadata_for_chunk(repository_id, index_version, chunk) -> dict[str, Any]:
    """Build ChromaDB-safe metadata (scalars only, no None values)."""
    return {
        "repository_id": str(repository_id),
        "index_version": str(index_version),
        "commit_sha": chunk.commit_sha,
        "file_path": chunk.file_path,
        "language": chunk.language,
        "chunk_type": chunk.chunk_type,
        "symbol_name": chunk.symbol_name or "",
        "parent_symbol": chunk.parent_symbol or "",
        "start_line": int(chunk.start_line),
        "end_line": int(chunk.end_line),
        "content_hash": chunk.content_hash,
        "chunk_strategy": chunk.chunk_strategy,
        "complete": str(bool(chunk.complete)),
        "partial": str(bool(chunk.partial)),
    }


def upsert_chunks(
    repository_id,
    index_version,
    chunks,
    embeddings,
) -> None:
    """Insert or replace chunks for one indexing run.

    ``chunks`` and ``embeddings`` are parallel lists. Chunk IDs are deterministic
    (repository + commit + file + symbol + lines), so re-indexing the same
    commit produces identical IDs; ChromaDB upserts by ID.
    """
    if len(chunks) != len(embeddings):
        raise VectorStoreError("Chunks and embeddings must be parallel lists.")
    if not chunks:
        return

    collection = _collection()
    try:
        collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[
                _metadata_for_chunk(repository_id, index_version, chunk)
                for chunk in chunks
            ],
            embeddings=[list(map(float, emb)) for emb in embeddings],
        )
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception("ChromaDB upsert failed for repository %s", repository_id)
        raise VectorStoreError("Chunks could not be stored in ChromaDB.") from exc

    logger.info(
        "Upserted %s chunks repository=%s index_version=%s",
        len(chunks),
        repository_id,
        index_version,
    )


def query_chunks(
    repository_id,
    index_version,
    query_embedding,
    *,
    top_k: int | None = None,
    min_relevance: float | None = None,
) -> list[ChunkRecord]:
    """Retrieve the most relevant chunks for a repository + active index.

    Cosine distance is converted to a similarity score in [0, 1] and chunks
    below ``min_relevance`` are dropped.
    """
    collection = _collection()
    top_k = settings.retrieval_top_k if top_k is None else top_k
    min_relevance = (
        settings.retrieval_min_relevance
        if min_relevance is None
        else min_relevance
    )

    try:
        results = collection.query(
            query_embeddings=[list(map(float, query_embedding))],
            n_results=top_k,
            where=_where(repository_id, index_version),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception(
            "ChromaDB query failed for repository %s index_version %s",
            repository_id,
            index_version,
        )
        raise VectorStoreError("Chunks could not be retrieved from ChromaDB.") from exc

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    records: list[ChunkRecord] = []
    for chunk_id, content, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite.
        similarity = max(0.0, min(1.0, 1.0 - float(distance)))
        if similarity < min_relevance:
            continue
        records.append(
            ChunkRecord(
                chunk_id=chunk_id,
                content=content,
                repository_id=str(metadata.get("repository_id", "")),
                commit_sha=str(metadata.get("commit_sha", "")),
                index_version=str(metadata.get("index_version", "")),
                file_path=str(metadata.get("file_path", "")),
                language=str(metadata.get("language", "")),
                chunk_type=str(metadata.get("chunk_type", "")),
                symbol_name=metadata.get("symbol_name") or None,
                parent_symbol=metadata.get("parent_symbol") or None,
                start_line=int(metadata.get("start_line", 0)),
                end_line=int(metadata.get("end_line", 0)),
                content_hash=str(metadata.get("content_hash", "")),
                chunk_strategy=str(metadata.get("chunk_strategy", "")),
                complete=str(metadata.get("complete", "false")) == "true",
                partial=str(metadata.get("partial", "false")) == "true",
                score=similarity,
            )
        )
    return records


def count_chunks(repository_id, index_version=None) -> int:
    """Return the number of stored chunks for a repository (+ optional index version)."""
    collection = _collection()
    where = _where(repository_id, index_version)
    try:
        result = collection.get(where=where, include=[])
        return len(result.get("ids", []))
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception(
            "ChromaDB count failed for repository %s", repository_id
        )
        raise VectorStoreError("Chunk count could not be read from ChromaDB.") from exc


def delete_repository_index(repository_id, index_version=None) -> None:
    """Delete all chunks for a repository, or for one index version.

    Used for safe cleanup when deactivating an old index version or deleting
    a repository. Never deletes chunks for another repository.
    """
    collection = _collection()
    where = _where(repository_id, index_version)
    try:
        collection.delete(where=where)
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception(
            "ChromaDB delete failed for repository %s index_version %s",
            repository_id,
            index_version,
        )
        raise VectorStoreError("Chunks could not be deleted from ChromaDB.") from exc

    logger.info(
        "Deleted ChromaDB chunks repository=%s index_version=%s",
        repository_id,
        index_version,
    )
