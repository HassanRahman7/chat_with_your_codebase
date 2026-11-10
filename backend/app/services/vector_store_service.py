"""In-memory vector store service with disk persistence.

Pure-Python replacement for ChromaDB that avoids the native Rust extension
crash on Windows with Smart App Control enabled. Stores chunk vectors in
memory and persists them to disk so indexed data survives backend restarts.

Owns all vector operations: upsert code chunks, query chunks filtered by
repository and active index version, and retire/delete index versions.
Vector details stay out of routers and RAG prompt code.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
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


# In-memory store: repository_id -> index_version -> list of chunk dicts.
# Each chunk dict has: id, content, metadata (dict), embedding (list[float]).
_vector_store: dict[str, dict[str, list[dict[str, Any]]]] = {}

_persist_file = settings.temporary_storage_directory / "vector_store.json"


def _load_from_disk() -> None:
    """Load persisted vector data from disk, if any."""
    global _vector_store
    try:
        if not _persist_file.exists():
            return
        with _persist_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        _vector_store = data
        logger.info(
            "Loaded vector store from %s (%s repositories)",
            _persist_file,
            len(_vector_store),
        )
    except Exception as exc:  # noqa: BLE001 - start with empty store on failure
        logger.warning(
            "Could not load vector store from %s: %s", _persist_file, exc
        )
        _vector_store = {}


def _save_to_disk() -> None:
    """Persist the in-memory vector store to disk."""
    try:
        _persist_file.parent.mkdir(parents=True, exist_ok=True)
        with _persist_file.open("w", encoding="utf-8") as f:
            json.dump(_vector_store, f)
    except Exception as exc:  # noqa: BLE001 - never fail indexing over persistence
        logger.warning("Could not persist vector store to %s: %s", _persist_file, exc)


# Load any previously persisted data at import time.
_load_from_disk()


def _store_for_repo(repository_id: str) -> dict[str, list[dict[str, Any]]]:
    return _vector_store.setdefault(str(repository_id), {})


def _where(repository_id, index_version: str | None = None) -> dict[str, Any]:
    """Build a where filter dict (mirrors the ChromaDB API shape)."""
    return {"repository_id": str(repository_id), "index_version": str(index_version) if index_version is not None else None}


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


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, in [0, 1]."""
    denom = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def upsert_chunks(
    repository_id,
    index_version,
    chunks,
    embeddings,
) -> None:
    """Insert or replace chunks for one indexing run.

    ``chunks`` and ``embeddings`` are parallel lists. Chunk IDs are deterministic
    (repository + commit + file + symbol + lines), so re-indexing the same
    commit produces identical IDs; upserts replace by ID.
    """
    if len(chunks) != len(embeddings):
        raise VectorStoreError("Chunks and embeddings must be parallel lists.")
    if not chunks:
        return

    repo_id = str(repository_id)
    iv = str(index_version)
    store = _store_for_repo(repo_id)
    existing = store.setdefault(iv, [])

    existing_by_id = {c["id"]: c for c in existing}
    for chunk, emb in zip(chunks, embeddings):
        existing_by_id[chunk.chunk_id] = {
            "id": chunk.chunk_id,
            "content": chunk.content,
            "metadata": _metadata_for_chunk(repository_id, index_version, chunk),
            "embedding": [float(x) for x in emb],
        }
    store[iv] = list(existing_by_id.values())

    _save_to_disk()

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

    Cosine similarity is computed with NumPy and chunks below ``min_relevance``
    are dropped.
    """
    repo_id = str(repository_id)
    iv = str(index_version)
    top_k = settings.retrieval_top_k if top_k is None else top_k
    min_relevance = (
        settings.retrieval_min_relevance
        if min_relevance is None
        else min_relevance
    )

    store = _vector_store.get(repo_id, {})
    chunks = store.get(iv, [])

    if not chunks:
        return []

    query_vec = np.array(list(map(float, query_embedding)), dtype=np.float32)
    query_norm = float(np.linalg.norm(query_vec))

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        vec = np.array(chunk["embedding"], dtype=np.float32)
        denom = query_norm * float(np.linalg.norm(vec))
        similarity = float(np.dot(query_vec, vec) / denom) if denom > 0.0 else 0.0
        similarity = max(0.0, min(1.0, similarity))
        if similarity >= min_relevance:
            scored.append((similarity, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:top_k]

    records: list[ChunkRecord] = []
    for similarity, chunk in top:
        metadata = chunk["metadata"]
        records.append(
            ChunkRecord(
                chunk_id=chunk["id"],
                content=chunk["content"],
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
    repo_id = str(repository_id)
    iv = str(index_version) if index_version is not None else None
    store = _vector_store.get(repo_id, {})
    if iv is None:
        return sum(len(c) for c in store.values())
    return len(store.get(iv, []))


def delete_repository_index(repository_id, index_version=None) -> None:
    """Delete all chunks for a repository, or for one index version.

    Used for safe cleanup when deactivating an old index version or deleting
    a repository. Never deletes chunks for another repository.
    """
    repo_id = str(repository_id)
    store = _vector_store.get(repo_id)
    if store is None:
        return

    if index_version is not None:
        iv = str(index_version)
        if iv in store:
            del store[iv]
            logger.info(
                "Deleted vector chunks repository=%s index_version=%s",
                repository_id,
                index_version,
            )
        if not store:
            del _vector_store[repo_id]
    else:
        del _vector_store[repo_id]
        logger.info(
            "Deleted vector chunks repository=%s (all index versions)",
            repository_id,
        )

    _save_to_disk()
