"""Domain errors that map to the public error envelope."""

from __future__ import annotations

from typing import Any

from app.api.error_handlers import AppError


class InvalidGitHubUrlError(AppError):
    status_code = 400
    code = "invalid_github_url"
    message = "Enter a supported public GitHub repository URL."


class RepositoryAlreadyExistsError(AppError):
    status_code = 409
    code = "repository_already_exists"
    message = "This repository is already registered."

    def __init__(self, repository_id: Any) -> None:
        super().__init__(details={"repository_id": str(repository_id)})


class RepositoryNotFoundError(AppError):
    status_code = 404
    code = "repository_not_found"
    message = "The requested repository could not be found."


class RepositoryConflictError(AppError):
    status_code = 409
    code = "repository_conflict"
    message = "The repository is not in a state that allows this operation."


class RepositoryDeletingError(AppError):
    status_code = 409
    code = "repository_deleting"
    message = "This repository is being deleted."


class IndexingConflictError(AppError):
    status_code = 409
    code = "indexing_in_progress"
    message = "An indexing job is already queued or running for this repository."


class IndexingDispatchError(AppError):
    status_code = 503
    code = "indexing_dispatch_failed"
    message = "The indexing job could not be started. Please try again."


class RepositoryCleanupError(AppError):
    status_code = 503
    code = "repository_cleanup_failed"
    message = "Repository cleanup could not be completed. Please try again."


class RepositoryCloneError(Exception):
    """Raised inside the worker when a clone cannot be completed."""

    def __init__(self, message: str, *, code: str = "repository_clone_failed") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RepositoryTooLargeError(RepositoryCloneError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="repository_too_large")


class RepositoryScanError(Exception):
    """Raised inside the worker when a repository cannot be scanned safely."""

    def __init__(self, message: str, *, code: str = "repository_scan_failed") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RepositoryTooManyFilesError(RepositoryScanError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="repository_too_many_files")


class NoSupportedSourceFilesError(RepositoryScanError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="no_supported_source_files")


class EmbeddingError(Exception):
    """Raised when the embedding model cannot encode text."""

    def __init__(self, message: str, *, code: str = "embedding_failed") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class VectorStoreError(Exception):
    """Raised when ChromaDB cannot store or retrieve vectors."""

    def __init__(self, message: str, *, code: str = "vector_store_failed") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ParserError(Exception):
    """Raised when source text cannot be decoded or parsed into a tree."""


class RepositoryDeletedMidIndexing(Exception):
    """Raised internally when a repository is deleted while indexing is running.

    The worker stops gracefully and does not mark the job as failed, because
    the repository is being intentionally removed.
    """
