"""Public status mapping tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.status_service import public_repository_status


def repo(status: str, active_index_version: str | None = None):
    return SimpleNamespace(
        status=status,
        active_index_version=active_index_version,
    )


def job(status: str = "running", step: str | None = None):
    return SimpleNamespace(status=status, current_step=step)


@pytest.mark.parametrize(
    ("internal", "expected"),
    [
        ("pending", "queued"),
        ("cloning", "cloning"),
        ("ready", "ready"),
        ("failed", "failed"),
        ("deleting", "deleting"),
    ],
)
def test_simple_internal_states_map_directly(internal: str, expected: str) -> None:
    assert public_repository_status(repo(internal)) == expected


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        ("validating_repository", "queued"),
        ("cloning_repository", "cloning"),
        ("discovering_files", "scanning"),
        ("parsing_files", "parsing"),
        ("creating_chunks", "parsing"),
        ("generating_embeddings", "embedding"),
        ("storing_vectors", "storing"),
        ("verifying_index", "storing"),
        ("activating_index", "storing"),
        ("completed", "ready"),
    ],
)
def test_indexing_steps_map_to_public_states(step: str, expected: str) -> None:
    assert public_repository_status(repo("indexing"), job(step=step)) == expected


def test_failed_initial_index_is_failed() -> None:
    assert public_repository_status(repo("indexing"), job(status="failed")) == "failed"


def test_failed_reindex_keeps_ready_when_active_index_exists() -> None:
    repository = repo("updating", active_index_version="v1")
    assert public_repository_status(repository, job(status="failed")) == "ready"


def test_unknown_state_is_queued() -> None:
    assert public_repository_status(repo("unexpected")) == "queued"
