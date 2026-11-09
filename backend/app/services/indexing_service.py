"""Background indexing worker.

Phase 2 completes validation, cloning, scanning, parsing and chunking. It
writes an inspectable JSONL chunk manifest and then stops before Phase 3 with
an explicit ``embedding_pipeline_pending`` result rather than pretending the
repository is ready for vector search.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.config import settings
from app.database.models import IndexingJob, Repository
from app.database.session import SessionLocal
from app.services.chunking_service import CodeChunker
from app.services.errors import RepositoryCloneError, RepositoryScanError
from app.services.file_scanner_service import scan_repository
from app.services.github_service import (
    canonicalize_github_url,
    clone_repository,
    repository_clone_path,
)

logger = logging.getLogger(__name__)

EMBEDDING_PENDING_CODE = "embedding_pipeline_pending"
EMBEDDING_PENDING_MESSAGE = (
    "Repository scanned and code chunks created. Embeddings and vector "
    "indexing are enabled in the next build phase."
)


def run_indexing_job(repository_id: UUID, job_id: UUID) -> None:
    """Run the Phase 1-2 indexing pipeline in a worker-owned session."""
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
                    manifest.write(json.dumps(asdict(chunk), default=str) + "\n")
                    total_chunks += 1

                job.files_processed += 1
                job.total_chunks = total_chunks
                completed_fraction = job.files_processed / discovered_count
                job.progress = 25 + round(50 * completed_fraction)
                job.current_step = (
                    "creating_chunks" if job.files_processed >= discovered_count // 2 else "parsing_files"
                )
                if job.files_processed % 25 == 0:
                    db.commit()

        job.current_step = "generating_embeddings"
        job.progress = 80
        db.commit()

        _fail_job(
            db,
            repository_id,
            job_id,
            EMBEDDING_PENDING_CODE,
            EMBEDDING_PENDING_MESSAGE,
        )

        logger.info(
            "Chunked repository id=%s files=%s chunks=%s manifest=%s",
            repository.id,
            job.files_processed,
            total_chunks,
            manifest_path,
        )
    except RepositoryCloneError as exc:
        _fail_job(db, repository_id, job_id, exc.code, exc.message)
    except RepositoryScanError as exc:
        _fail_job(db, repository_id, job_id, exc.code, exc.message)
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
