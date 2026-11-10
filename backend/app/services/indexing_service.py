"""Background indexing worker.

Completes the full Phase 1-3 indexing pipeline:

1. Validate the GitHub URL
2. Shallow-clone the repository and record the commit SHA
3. Scan eligible source files (exclusions, size/path safety)
4. Parse with Tree-sitter and create syntax-aware chunks
5. Generate embeddings with the configured Sentence Transformer model
6. Upsert chunk vectors into ChromaDB, filtered by repository + index version
7. Verify the vector count matches the chunk count
8. Activate the new index version and mark the repository READY

A failed new index never replaces a previously valid active index.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.config import settings
from app.database.models import IndexingJob, Repository
from app.database.session import SessionLocal
from app.services.chunking_service import CodeChunk, CodeChunker
from app.services.embedding_service import encode_texts
from app.services.errors import (
    EmbeddingError,
    RepositoryCloneError,
    RepositoryDeletedMidIndexing,
    RepositoryScanError,
    VectorStoreError,
)
from app.services.file_scanner_service import scan_repository
from app.services.github_service import (
    canonicalize_github_url,
    clone_repository,
    repository_clone_path,
)
from app.services.vector_store_service import count_chunks, upsert_chunks
from sqlalchemy.orm.exc import StaleDataError

logger = logging.getLogger(__name__)

EMBEDDING_PENDING_CODE = "embedding_pipeline_pending"
EMBEDDING_PENDING_MESSAGE = (
    "Repository scanned and code chunks created. Embeddings and vector "
    "indexing are enabled in the next build phase."
)


def run_indexing_job(repository_id: UUID, job_id: UUID) -> None:
    """Run the complete indexing pipeline in a worker-owned database session."""
    db = SessionLocal()
    try:
        job = db.get(IndexingJob, job_id)
        repository = db.get(Repository, repository_id)
        if job is None or repository is None:
            logger.warning(
                "Skipping indexing job_id=%s repository_id=%s: record missing",
                job_id,
                repository_id,
            )
            return
        if job.status != "queued":
            logger.info("Skipping indexing job_id=%s: status=%s", job_id, job.status)
            return

        now = datetime.now(timezone.utc)
        job.status = "running"
        job.started_at = now
        job.current_step = "validating_repository"
        job.progress = 2
        db.commit()

        parsed = canonicalize_github_url(repository.github_url)

        repository.status = "cloning"
        job.current_step = "cloning_repository"
        job.progress = 5
        db.commit()

        clone_result = clone_repository(
            parsed.canonical_url,
            repository_clone_path(repository.id),
            timeout_seconds=settings.clone_timeout_seconds,
        )

        repository.default_branch = clone_result.default_branch
        repository.local_path = clone_result.local_path
        repository.last_checked_at = datetime.now(timezone.utc)
        repository.status = "indexing"
        job.commit_sha = clone_result.commit_sha
        job.current_step = "discovering_files"
        job.progress = 12
        db.commit()

        scan_result = scan_repository(Path(clone_result.local_path))
        job.files_discovered = len(scan_result.files)
        job.files_processed = 0
        job.total_chunks = 0
        job.current_step = "parsing_files"
        job.progress = 25
        db.commit()

        logger.info(
            "Scanned repository id=%s files=%s skipped=%s",
            repository.id,
            len(scan_result.files),
            len(scan_result.skipped),
        )

        # One deterministic index version per successful indexing run.
        index_version = uuid.uuid4()
        job.index_version = str(index_version)
        db.commit()

        manifest_path = _manifest_path(repository.id, job.id)
        chunker = CodeChunker()
        total_chunks = 0
        discovered_count = max(1, len(scan_result.files))

        with manifest_path.open("w", encoding="utf-8") as manifest:
            for source_file in scan_result.files:
                chunks = chunker.process_source_file(
                    repository_id=repository.id,
                    commit_sha=clone_result.commit_sha,
                    source_file=source_file,
                )
                for chunk in chunks:
                    manifest.write(json.dumps(_chunk_to_dict(chunk)) + "\n")
                    total_chunks += 1

                job.files_processed += 1
                job.total_chunks = total_chunks
                completed_fraction = job.files_processed / discovered_count
                job.progress = 25 + round(20 * completed_fraction)
                job.current_step = (
                    "creating_chunks"
                    if job.files_processed >= discovered_count // 2
                    else "parsing_files"
                )
                if job.files_processed % 25 == 0:
                    db.commit()

        job.total_chunks = total_chunks
        job.current_step = "generating_embeddings"
        job.progress = 50
        db.commit()

        logger.info(
            "Chunked repository id=%s files=%s chunks=%s manifest=%s",
            repository.id,
            job.files_processed,
            total_chunks,
            manifest_path,
        )

        # Phase 3: embeddings + vector storage.
        _embed_and_store(
            db,
            repository,
            job,
            index_version,
            manifest_path,
            total_chunks,
        )

        logger.info(
            "Indexed repository id=%s commit=%s index_version=%s chunks=%s",
            repository.id,
            clone_result.commit_sha,
            index_version,
            total_chunks,
        )
    except RepositoryCloneError as exc:
        _fail_job(db, repository_id, job_id, exc.code, exc.message)
    except RepositoryScanError as exc:
        _fail_job(db, repository_id, job_id, exc.code, exc.message)
    except (EmbeddingError, VectorStoreError) as exc:
        _fail_job(db, repository_id, job_id, exc.code, exc.message)
    except RepositoryDeletedMidIndexing:
        # The repository was deleted while indexing was running. Stop
        # gracefully without marking the job as failed.
        logger.info(
            "Repository deleted mid-indexing repository_id=%s job_id=%s",
            repository_id,
            job_id,
        )
    except Exception:  # noqa: BLE001 - worker must never leak internals
        logger.exception(
            "Unexpected indexing failure repository_id=%s job_id=%s",
            repository_id,
            job_id,
        )
        _fail_job(
            db,
            repository_id,
            job_id,
            "indexing_internal_error",
            "Indexing could not be completed. Please try again.",
        )
    finally:
        db.close()


def _safe_commit(db) -> bool:
    """Commit pending changes.

    Returns ``False`` if the commit failed because a row was deleted by a
    concurrent operation (for example, the repository was deleted while the
    worker was running). In that case the transaction is rolled back and the
    worker should stop processing.
    """
    try:
        db.commit()
        return True
    except StaleDataError:
        db.rollback()
        return False


def _embed_and_store(
    db,
    repository: Repository,
    job: IndexingJob,
    index_version: UUID,
    manifest_path: Path,
    total_chunks: int,
) -> None:
    """Read the chunk manifest, embed in batches, upsert to ChromaDB, verify, activate."""
    # ChromaDB upsert batch size: larger than the embedding sub-batch size so
    # we make fewer (larger) ChromaDB write calls while still sub-batching
    # through the embedding model.
    chroma_batch_size = 256
    batch_texts: list[str] = []
    batch_chunks: list[dict[str, Any]] = []
    stored = 0

    def flush_batch() -> None:
        nonlocal stored
        if not batch_chunks:
            return
        embeddings = encode_texts(batch_texts)
        upsert_chunks(repository.id, index_version, batch_chunks, embeddings)
        stored += len(batch_chunks)
        job.progress = 50 + round(35 * stored / max(1, total_chunks))
        job.current_step = "storing_vectors"
        if not _safe_commit(db):
            # The repository was deleted while indexing was running; stop.
            raise RepositoryDeletedMidIndexing()

    with manifest_path.open("r", encoding="utf-8") as manifest:
        for line in manifest:
            line = line.strip()
            if not line:
                continue
            chunk_data = json.loads(line)
            batch_texts.append(chunk_data["content"])
            batch_chunks.append(_dict_to_chunk(chunk_data))
            if len(batch_chunks) >= chroma_batch_size:
                flush_batch()

    flush_batch()

    # Verify the vector count matches the chunk count before activating.
    job.current_step = "verifying_index"
    job.progress = 90
    if not _safe_commit(db):
        raise RepositoryDeletedMidIndexing()

    stored_count = count_chunks(repository.id, str(index_version))
    if stored_count != total_chunks:
        raise VectorStoreError(
            f"Vector verification failed: expected {total_chunks} chunks, "
            f"stored {stored_count}."
        )

    # Activate the new index version. The previous active index (if any)
    # remains in ChromaDB but is no longer the active pointer.
    job.current_step = "activating_index"
    job.progress = 98
    if not _safe_commit(db):
        raise RepositoryDeletedMidIndexing()

    now = datetime.now(timezone.utc)
    repository.active_index_version = str(index_version)
    repository.active_commit_sha = job.commit_sha
    repository.status = "ready"
    repository.indexed_at = now
    repository.last_error = None
    job.status = "succeeded"
    job.current_step = "completed"
    job.progress = 100
    job.completed_at = now
    if not _safe_commit(db):
        raise RepositoryDeletedMidIndexing()


def _chunk_to_dict(chunk: CodeChunk) -> dict[str, Any]:
    """Serialize a CodeChunk dataclass to a JSON-friendly dict."""
    data = {}
    for field in fields(chunk):
        value = getattr(chunk, field.name)
        if isinstance(value, UUID):
            value = str(value)
        data[field.name] = value
    return data


def _dict_to_chunk(data: dict[str, Any]) -> CodeChunk:
    """Rebuild a CodeChunk from a manifest JSON dict."""
    return CodeChunk(
        chunk_id=data["chunk_id"],
        repository_id=UUID(data["repository_id"]),
        commit_sha=data["commit_sha"],
        file_path=data["file_path"],
        language=data["language"],
        chunk_type=data["chunk_type"],
        symbol_name=data.get("symbol_name"),
        parent_symbol=data.get("parent_symbol"),
        start_line=int(data["start_line"]),
        end_line=int(data["end_line"]),
        content=data["content"],
        content_hash=data["content_hash"],
        chunk_strategy=data["chunk_strategy"],
        complete=bool(data["complete"]),
        partial=bool(data["partial"]),
        parent_context=data.get("parent_context"),
        part_index=data.get("part_index"),
        part_count=data.get("part_count"),
    )


def _manifest_path(repository_id: UUID, job_id: UUID) -> Path:
    settings.ensure_storage_directories()
    return settings.temporary_storage_directory / f"chunks-{repository_id}-{job_id}.jsonl"


def _fail_job(
    db,
    repository_id: UUID,
    job_id: UUID,
    code: str,
    message: str,
) -> None:
    """Record a safe terminal failure without replacing a valid active index."""
    try:
        db.rollback()
        job = db.get(IndexingJob, job_id)
        repository = db.get(Repository, repository_id)
        if job is None:
            return
        if job.status in {"succeeded", "failed", "cancelled"}:
            return

        job.status = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        if job.current_step is None:
            job.current_step = "validating_repository"

        if repository is not None:
            repository.last_error = message
            repository.status = (
                "ready" if repository.active_index_version else "failed"
            )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "Could not record indexing failure repository_id=%s job_id=%s",
            repository_id,
            job_id,
        )
