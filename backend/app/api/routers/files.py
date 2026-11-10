"""File tree and source content endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.error_handlers import AppError
from app.database.session import get_db
from app.schemas.common import PaginationResponse
from app.services import file_service

router = APIRouter(prefix="/repositories", tags=["Files"])


@router.get(
    "/{repository_id}/files",
    summary="Get repository file tree",
    responses={
        404: {"description": "Repository not found"},
        409: {"description": "Repository has no active indexed source snapshot"},
    },
)
def get_repository_files(
    repository_id: UUID = Path(..., description="Repository UUID"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the nested file tree for the repository's active source snapshot."""
    _repository, tree = file_service.get_file_tree(repository_id)
    if not tree and _repository.local_path is None:
        raise AppError(
            message="This repository has no active indexed source snapshot.",
            code="repository_not_indexed",
            status_code=409,
        )
    return {
        "repository_id": str(repository_id),
        "items": tree,
    }


@router.get(
    "/{repository_id}/files/content",
    summary="Get source file content",
    responses={
        404: {"description": "Repository or file does not exist"},
        409: {"description": "Invalid relative directory path or repository not indexed"},
        422: {"description": "Invalid relative path"},
    },
)
def get_file_content(
    repository_id: UUID = Path(..., description="Repository UUID"),
    path: str = Query(..., description="Repository-relative file path"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the contents and metadata of one repository-relative source file."""
    (
        _repository,
        content,
        language,
        size_bytes,
        commit_sha,
    ) = file_service.get_file_content(repository_id, path)
    return {
        "repository_id": str(repository_id),
        "path": path,
        "content": content,
        "language": language,
        "size_bytes": size_bytes,
        "commit_sha": commit_sha,
    }
