"""Indexing job and repository-status endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.indexing import (
    ActiveIndexResponse,
    IndexingJobResponse,
    IndexingStartRequest,
    IndexingStartResponse,
    RepositoryStatusResponse,
)
from app.services import indexing_service, repository_service
from app.services.status_service import public_repository_status

router = APIRouter(prefix="/repositories", tags=["Indexing"])


@router.post(
    "/{repository_id}/index",
    response_model=IndexingStartResponse,
    status_code=202,
    summary="Queue a new indexing job",
    responses={
        404: {"description": "Repository not found"},
        409: {"description": "An indexing job is already active"},
        503: {"description": "The job could not be queued"},
    },
)
def start_indexing(
    repository_id: UUID,
    background_tasks: BackgroundTasks,
    payload: IndexingStartRequest | None = None,
    db: Session = Depends(get_db),
) -> IndexingStartResponse:
    repository, job = repository_service.start_indexing(
        db,
        repository_id,
        force=payload.force if payload else False,
    )
    background_tasks.add_task(
        indexing_service.run_indexing_job, repository.id, job.id
    )
    return IndexingStartResponse(
        repository_id=repository.id,
        indexing_job=IndexingJobResponse.model_validate(job),
    )


@router.get(
    "/{repository_id}/status",
    response_model=RepositoryStatusResponse,
    summary="Get the latest indexing status",
    responses={404: {"description": "Repository not found"}},
)
def repository_status(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> RepositoryStatusResponse:
    repository = repository_service.get_repository(db, repository_id)
    latest_job = repository_service.get_latest_job(db, repository_id)
    active_index = None
    if repository.active_commit_sha and repository.active_index_version:
        active_index = ActiveIndexResponse(
            commit_sha=repository.active_commit_sha,
            is_available=True,
        )
    return RepositoryStatusResponse(
        repository_id=repository.id,
        repository_status=public_repository_status(repository, latest_job),
        job=(
            IndexingJobResponse.model_validate(latest_job)
            if latest_job is not None
            else None
        ),
        active_index=active_index,
    )
