"""Map internal persistence states to the public repository lifecycle vocabulary."""

from __future__ import annotations

from typing import Any

PUBLIC_STATUSES = (
    "queued",
    "cloning",
    "scanning",
    "parsing",
    "embedding",
    "storing",
    "ready",
    "failed",
    "deleting",
)

_STEP_TO_PUBLIC = {
    "validating_repository": "queued",
    "cloning_repository": "cloning",
    "discovering_files": "scanning",
    "parsing_files": "parsing",
    "creating_chunks": "parsing",
    "generating_embeddings": "embedding",
    "storing_vectors": "storing",
    "verifying_index": "storing",
    "activating_index": "storing",
    "completed": "ready",
}


def public_repository_status(
    repository: Any,
    latest_job: Any | None = None,
) -> str:
    """Return one of the nine public states documented in ``API.md``."""
    internal = getattr(repository, "status", "pending")
    has_active_index = bool(getattr(repository, "active_index_version", None))

    if internal == "pending":
        return "queued"
    if internal == "cloning":
        return "cloning"
    if internal == "ready":
        return "ready"
    if internal == "failed":
        return "failed"
    if internal == "deleting":
        return "deleting"

    if internal in {"indexing", "updating"}:
        if latest_job is not None:
            job_status = getattr(latest_job, "status", None)
            if job_status in {"failed", "cancelled"}:
                if internal == "updating" and has_active_index:
                    return "ready"
                return "failed"
            step = getattr(latest_job, "current_step", None)
            if step in _STEP_TO_PUBLIC:
                return _STEP_TO_PUBLIC[step]
        return "scanning"

    return "queued"
