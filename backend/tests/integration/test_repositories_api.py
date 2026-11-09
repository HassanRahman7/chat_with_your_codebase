"""Phase 1 repository API integration tests."""

from __future__ import annotations

import shutil
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.models import IndexingJob, Repository
from app.services.github_service import repository_clone_path


def _create(client, url: str = "https://github.com/octocat/Hello-World"):
    return client.post("/api/repositories", json={"github_url": url})


def test_create_repository_returns_queued_contract(client) -> None:
    response = _create(client)

    assert response.status_code == 201
    body = response.json()
    assert body["repository"]["github_url"] == "https://github.com/octocat/hello-world"
    assert body["repository"]["repository_name"] == "hello-world"
    assert body["repository"]["owner_name"] == "octocat"
    assert body["repository"]["status"] == "queued"
    assert body["repository"]["created_at"].endswith("Z")
    assert body["indexing_job"]["status"] == "queued"
    assert body["indexing_job"]["current_step"] == "validating_repository"
    assert body["indexing_job"]["progress"] == 0

    repository_id = body["repository"]["id"]
    detail = client.get(f"/api/repositories/{repository_id}")
    assert detail.status_code == 200
    assert detail.json()["latest_indexing_job"]["id"] == body["indexing_job"]["id"]

    status = client.get(f"/api/repositories/{repository_id}/status")
    assert status.status_code == 200
    assert status.json()["repository_status"] == "queued"
    assert status.json()["job"]["status"] == "queued"
    assert status.json()["active_index"] is None


def test_duplicate_repository_is_rejected_with_existing_id(client) -> None:
    first = _create(client)
    repository_id = first.json()["repository"]["id"]

    duplicate = _create(client, "https://www.github.com/OctoCat/Hello-World.git/")

    assert duplicate.status_code == 409
    error = duplicate.json()["error"]
    assert error["code"] == "repository_already_exists"
    assert error["details"]["repository_id"] == repository_id


def test_invalid_url_uses_standard_error_envelope(client) -> None:
    response = _create(client, "https://gitlab.com/octocat/hello-world")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_github_url"
    assert error["message"]
    assert error["request_id"].startswith("req_")


def test_missing_and_invalid_request_fields_are_422(client) -> None:
    missing = client.post("/api/repositories", json={})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_error"

    empty = client.post("/api/repositories", json={"github_url": "   "})
    assert empty.status_code == 422

    malformed_id = client.get("/api/repositories/not-a-uuid")
    assert malformed_id.status_code == 422
    assert malformed_id.json()["error"]["code"] == "validation_error"


def test_list_repositories_paginates(client) -> None:
    _create(client, "https://github.com/octocat/Hello-World")
    _create(client, "https://github.com/octocat/Spoon-Knife")

    first = client.get("/api/repositories", params={"limit": 1, "offset": 0})
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["pagination"] == {
        "limit": 1,
        "offset": 0,
        "total": 2,
        "has_more": True,
    }
    assert len(first_body["items"]) == 1

    second = client.get("/api/repositories", params={"limit": 1, "offset": 1})
    assert second.status_code == 200
    assert second.json()["pagination"]["has_more"] is False
    assert len(second.json()["items"]) == 1

    invalid = client.get("/api/repositories", params={"limit": 0})
    assert invalid.status_code == 422


def test_status_reflects_indexing_step(client, db_session) -> None:
    created = _create(client)
    repository_id = UUID(created.json()["repository"]["id"])
    job_id = UUID(created.json()["indexing_job"]["id"])

    repository = db_session.get(Repository, repository_id)
    job = db_session.get(IndexingJob, job_id)
    assert repository is not None and job is not None
    repository.status = "indexing"
    job.status = "running"
    job.current_step = "discovering_files"
    db_session.commit()

    response = client.get(f"/api/repositories/{repository_id}/status")

    assert response.status_code == 200
    assert response.json()["repository_status"] == "scanning"
    assert response.json()["job"]["current_step"] == "discovering_files"


def test_index_conflict_then_retry_queues_new_job(client, db_session) -> None:
    created = _create(client)
    repository_id = UUID(created.json()["repository"]["id"])
    first_job_id = UUID(created.json()["indexing_job"]["id"])

    conflict = client.post(
        f"/api/repositories/{repository_id}/index", json={"force": True}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "indexing_in_progress"

    first_job = db_session.get(IndexingJob, first_job_id)
    assert first_job is not None
    first_job.status = "failed"
    db_session.commit()

    retried = client.post(f"/api/repositories/{repository_id}/index")
    assert retried.status_code == 202
    body = retried.json()
    assert body["repository_id"] == str(repository_id)
    assert body["indexing_job"]["status"] == "queued"
    assert body["indexing_job"]["id"] != str(first_job_id)

    jobs = list(
        db_session.scalars(
            select(IndexingJob).where(IndexingJob.repository_id == repository_id)
        )
    )
    assert len(jobs) == 2


def test_delete_repository_removes_clone_and_records(client, db_session) -> None:
    created = _create(client)
    repository_id = UUID(created.json()["repository"]["id"])
    job_id = UUID(created.json()["indexing_job"]["id"])

    clone_path = repository_clone_path(repository_id)
    clone_path.mkdir(parents=True, exist_ok=True)
    (clone_path / "README.md").write_text("temporary", encoding="utf-8")
    repository = db_session.get(Repository, repository_id)
    assert repository is not None
    repository.local_path = str(clone_path)
    db_session.commit()

    try:
        response = client.delete(f"/api/repositories/{repository_id}")
        assert response.status_code == 204
        assert not clone_path.exists()
        assert client.get(f"/api/repositories/{repository_id}").status_code == 404
        assert db_session.get(Repository, repository_id) is None
        assert db_session.get(IndexingJob, job_id) is None
    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


def test_missing_repository_operations_return_404(client) -> None:
    missing = uuid4()

    assert client.get(f"/api/repositories/{missing}").status_code == 404
    assert client.get(f"/api/repositories/{missing}/status").status_code == 404
    assert client.delete(f"/api/repositories/{missing}").status_code == 404
    assert client.post(f"/api/repositories/{missing}/index", json={}).status_code == 404
