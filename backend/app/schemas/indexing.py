"""Pydantic contracts for indexing jobs and repository status."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import APIModel


class IndexingJobResponse(APIModel):
    id: UUID
    status: str
    current_step: str | None = None
    progress: int
    files_discovered: int
    files_processed: int
    total_chunks: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None


class IndexingStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False


class IndexingStartResponse(APIModel):
    repository_id: UUID
    indexing_job: IndexingJobResponse


class ActiveIndexResponse(APIModel):
    commit_sha: str
    is_available: bool


class RepositoryStatusResponse(APIModel):
    repository_id: UUID
    repository_status: str
    job: IndexingJobResponse | None = None
    active_index: ActiveIndexResponse | None = None
