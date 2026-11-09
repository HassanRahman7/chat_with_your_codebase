"""Repository registration and lifecycle endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.indexing import IndexingJobResponse
from app.schemas.repository import (
    RepositoryCreateRequest,
    RepositoryCreateResponse,
    RepositoryDetailResponse,
    RepositoryListResponse,
    RepositoryResponse,
)
from app.schemas.common import PaginationResponse
from app.services import indexing_service, repository_service
from app.services.status_service import public_repository_status

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post(
    "",
    response_model=RepositoryCreateResponse,
    status_code=201,
    summary="Register and queue a public GitHub repository",
    responses={
        400: {"description": "Unsupported or malformed GitHub URL"},
        409: {"description": "Repository is already registered"},
    },
)
def create_repository(
    payload: RepositoryCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RepositoryCreateResponse:
    repository, job = repository_service.create_repository(db, payload.github_url)
    background_tasks.add_task(
        indexing_service.run_indexing_job, repository.id, job.id
    )
    return RepositoryCreateResponse(
        repository=RepositoryResponse.from_model(
            repository, public_repository_status(repository, job)
        ),
        indexing_job=IndexingJobResponse.model_validate(job),
    )


@router.get(
    "",
    response_model=RepositoryListResponse,
    summary="List registered repositories",
)
def list_repositories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RepositoryListResponse:
    repositories, total = repository_service.list_repositories(
        db, limit=limit, offset=offset
    )
    latest_jobs = repository_service.get_latest_jobs(
        db, [repository.id for repository in repositories]
    )
    items = [
        RepositoryResponse.from_model(
            repository,
            public_repository_status(repository, latest_jobs.get(repository.id)),
        )
        for repository in repositories
    ]
    return RepositoryListResponse(
        items=items,
        pagination=PaginationResponse(
            limit=limit,
            offset=offset,
            total=total,
            has_more=offset + len(items) < total,
        ),
    )


@router.get(
    "/{repository_id}",
    response_model=RepositoryDetailResponse,
    summary="Get repository details",
    responses={404: {"description": "Repository not found"}},
)
def get_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> RepositoryDetailResponse:
    repository = repository_service.get_repository(db, repository_id)
    latest_job = repository_service.get_latest_job(db, repository_id)
    return RepositoryDetailResponse.from_model_with_job(
        repository,
        public_repository_status(repository, latest_job),
        latest_job,
    )


@router.delete(
    "/{repository_id}",
    status_code=204,
    summary="Delete a repository and its local clone",
    responses={
        404: {"description": "Repository not found"},
        409: {"description": "Repository is already being deleted"},
        503: {"description": "Cleanup could not be completed"},
    },
)
def delete_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    repository_service.delete_repository(db, repository_id)
    return Response(status_code=204)
