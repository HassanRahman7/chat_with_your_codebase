"""Pydantic contracts for repository endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import APIModel, PaginationResponse
from app.schemas.indexing import IndexingJobResponse


class RepositoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    github_url: str = Field(min_length=1, max_length=2048)

    @field_validator("github_url")
    @classmethod
    def _validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A GitHub repository URL is required.")
        return value


class RepositoryResponse(APIModel):
    id: UUID
    github_url: str
    repository_name: str
    owner_name: str | None = None
    default_branch: str | None = None
    status: str
    active_commit_sha: str | None = None
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None = None

    @classmethod
    def from_model(cls, repository: Any, public_status: str) -> "RepositoryResponse":
        return cls(
            id=repository.id,
            github_url=repository.github_url,
            repository_name=repository.repository_name,
            owner_name=repository.owner_name,
            default_branch=repository.default_branch,
            status=public_status,
            active_commit_sha=repository.active_commit_sha,
            created_at=repository.created_at,
            updated_at=repository.updated_at,
            indexed_at=repository.indexed_at,
        )


class RepositoryDetailResponse(RepositoryResponse):
    latest_indexing_job: IndexingJobResponse | None = None

    @classmethod
    def from_model_with_job(
        cls,
        repository: Any,
        public_status: str,
        latest_job: Any | None,
    ) -> "RepositoryDetailResponse":
        base = RepositoryResponse.from_model(repository, public_status)
        return cls(
            **base.model_dump(),
            latest_indexing_job=(
                IndexingJobResponse.model_validate(latest_job) if latest_job else None
            ),
        )


class RepositoryListResponse(APIModel):
    items: list[RepositoryResponse]
    pagination: PaginationResponse


class RepositoryCreateResponse(APIModel):
    repository: RepositoryResponse
    indexing_job: IndexingJobResponse


class RepositoryDeleteResponse(APIModel):
    repository_id: UUID
    status: str
    message: str
