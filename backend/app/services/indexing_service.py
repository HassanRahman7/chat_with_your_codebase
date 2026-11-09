"""Background indexing worker.

Phase 1 performs validation, cloning and commit capture. Parsing, chunking,
embeddings and vector storage are layered on in later phases. Until that
pipeline exists the job terminates with an explicit ``indexing_pipeline_pending``
result rather than pretending the repository is ready.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.config import settings
from app.database.models import IndexingJob, Repository
from app.database.session import SessionLocal
from app.services.errors import RepositoryCloneError
from app.services.github_service import (
    canonicalize_github_url,
    clone_repository,
    repository_clone_path,
)

logger = logging.getLogger(__name__)

PIPELINE_PENDING_CODE = "indexing_pipeline_pending"
PIPELINE_PENDING_MESSAGE = (
    "Repository cloned successfully. Code parsing and indexing are enabled in "
    "the next build phase."
)


def run_indexing_job(repository_id: UUID, job_id: UUID) -> None:
    """Clone a registered repository in a worker-owned database session."""
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
        job.current_step = "cloning_repository"
        job.progress = 10
        db.commit()

        # Phase 1 boundary. Later phases replace this block with scanning,
        # parsing, embedding, storage, verification and activation.
        message = PIPELINE_PENDING_MESSAGE
        job.status = "failed"
        job.error_code = PIPELINE_PENDING_CODE
        job.error_message = message
        job.progress = 10
        job.completed_at = datetime.now(timezone.utc)
        repository.status = "failed"
        repository.last_error = message
        db.commit()

        logger.info(
            "Cloned repository id=%s at commit=%s; indexing pipeline pending",
            repository.id,
            clone_result.commit_sha,
        )
    except RepositoryCloneError as exc:
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
            # A failed re-index must not hide a usable previous index.
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
