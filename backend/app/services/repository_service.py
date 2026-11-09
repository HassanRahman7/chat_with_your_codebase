"""Repository registration, lookup, re-indexing and deletion services."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import IndexingJob, Repository
from app.services.errors import (
    IndexingConflictError,
    RepositoryAlreadyExistsError,
    RepositoryCleanupError,
    RepositoryDeletingError,
    RepositoryNotFoundError,
)
from app.services.github_service import (
    canonicalize_github_url,
    remove_repository_directory,
    repository_clone_path,
)

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = ("queued", "running")


def create_repository(db: Session, raw_url: str) -> tuple[Repository, IndexingJob]:
    """Register a canonical public GitHub repository and queue its first job."""
    parsed = canonicalize_github_url(raw_url)

    existing = db.scalar(
        select(Repository).where(Repository.github_url == parsed.canonical_url)
    )
    if existing is not None:
        raise RepositoryAlreadyExistsError(existing.id)

    repository = Repository(
        github_url=parsed.canonical_url,
        repository_name=parsed.name,
        owner_name=parsed.owner,
        status="pending",
    )
    db.add(repository)
    try:
        db.flush()
        job = IndexingJob(
            repository_id=repository.id,
            status="queued",
            current_step="validating_repository",
            progress=0,
        )
        db.add(job)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(Repository).where(Repository.github_url == parsed.canonical_url)
        )
        if existing is not None:
            raise RepositoryAlreadyExistsError(existing.id) from exc
        raise

    db.refresh(repository)
    db.refresh(job)
    logger.info(
        "Registered repository id=%s name=%s job_id=%s",
        repository.id,
        repository.github_url,
        job.id,
    )
    return repository, job


def get_repository(db: Session, repository_id: UUID) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None:
        raise RepositoryNotFoundError()
    return repository


def list_repositories(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Repository], int]:
    total = db.scalar(select(func.count()).select_from(Repository)) or 0
    items = list(
        db.scalars(
            select(Repository)
            .order_by(Repository.created_at.desc(), Repository.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return items, total


def get_latest_job(db: Session, repository_id: UUID) -> IndexingJob | None:
    return db.scalar(
        select(IndexingJob)
        .where(IndexingJob.repository_id == repository_id)
        .order_by(IndexingJob.created_at.desc(), IndexingJob.id.desc())
        .limit(1)
    )


def get_latest_jobs(
    db: Session,
    repository_ids: list[UUID],
) -> dict[UUID, IndexingJob]:
    """Return the latest job for each repository in one query."""
    if not repository_ids:
        return {}

    jobs = list(
        db.scalars(
            select(IndexingJob)
            .where(IndexingJob.repository_id.in_(repository_ids))
            .order_by(
                IndexingJob.repository_id,
                IndexingJob.created_at.desc(),
                IndexingJob.id.desc(),
            )
        )
    )
    latest: dict[UUID, IndexingJob] = {}
    for job in jobs:
        latest.setdefault(job.repository_id, job)
    return latest


def get_active_job(db: Session, repository_id: UUID) -> IndexingJob | None:
    return db.scalar(
        select(IndexingJob)
        .where(
            IndexingJob.repository_id == repository_id,
            IndexingJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        .order_by(IndexingJob.created_at.desc(), IndexingJob.id.desc())
        .limit(1)
    )


def start_indexing(
    db: Session,
    repository_id: UUID,
    *,
    force: bool = False,
) -> tuple[Repository, IndexingJob]:
    """Queue a new indexing job, rejecting duplicate active work."""
    repository = db.scalar(
        select(Repository).where(Repository.id == repository_id).with_for_update()
    )
    if repository is None:
        raise RepositoryNotFoundError()
    if repository.status == "deleting":
        raise RepositoryDeletingError()

    active_job = get_active_job(db, repository_id)
    if active_job is not None:
        raise IndexingConflictError()

    # ``force`` is accepted now so the public contract is stable. Remote commit
    # comparison is added with the indexing pipeline; until then a new request
    # is always a fresh indexing attempt.
    _ = force

    repository.status = (
        "updating" if repository.active_index_version else "pending"
    )
    repository.last_error = None
    job = IndexingJob(
        repository_id=repository.id,
        status="queued",
        current_step="validating_repository",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(repository)
    db.refresh(job)
    logger.info(
        "Queued re-index repository id=%s job_id=%s", repository.id, job.id
    )
    return repository, job


def delete_repository(db: Session, repository_id: UUID) -> None:
    """Remove a repository clone and its relational records.

    Phase 1 performs cleanup synchronously because no vector index exists yet.
    ChromaDB cleanup is added with the vector-store phase. If filesystem cleanup
    fails, the record remains in the ``deleting`` state so it is not silently
    orphaned.
    """
    repository = db.scalar(
        select(Repository).where(Repository.id == repository_id).with_for_update()
    )
    if repository is None:
        raise RepositoryNotFoundError()
    if repository.status == "deleting":
        raise RepositoryDeletingError()

    repository.status = "deleting"
    db.commit()

    clone_path = repository.local_path or repository_clone_path(repository.id)
    try:
        remove_repository_directory(clone_path)
    except Exception as exc:  # noqa: BLE001 - converted to a safe public error
        logger.exception("Repository cleanup failed for id=%s", repository.id)
        raise RepositoryCleanupError() from exc

    try:
        db.delete(repository)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Repository database deletion failed for id=%s", repository.id)
        raise RepositoryCleanupError() from exc

    logger.info("Deleted repository id=%s", repository_id)


def repository_display_name(repository: Any) -> str:
    owner = getattr(repository, "owner_name", None)
    name = getattr(repository, "repository_name", "")
    return f"{owner}/{name}" if owner else name
