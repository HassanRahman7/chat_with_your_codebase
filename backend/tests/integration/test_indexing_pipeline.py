"""Phase 2 indexing pipeline integration test."""

from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.models import IndexingJob, Repository
from app.services import indexing_service
from app.services.github_service import CloneResult


def _write(root, relative, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _create_job(db_session):
    repository = Repository(
        github_url="https://github.com/octocat/hello-world",
        repository_name="hello-world",
        owner_name="octocat",
        status="pending",
    )
    db_session.add(repository)
    db_session.flush()
    job = IndexingJob(
        repository_id=repository.id,
        status="queued",
        current_step="validating_repository",
        progress=0,
    )
    db_session.add(job)
    db_session.commit()
    return repository.id, job.id


def test_worker_scans_parses_and_chunks_repository(
    db_session,
    test_engine,
    tmp_path,
    monkeypatch,
):
    repository_id, job_id = _create_job(db_session)
    clone_root = tmp_path / "clone"
    temporary = tmp_path / "temporary"
    _write(clone_root, "src/main.py", "def add(a, b):\n    return a + b\n")
    _write(
        clone_root,
        "src/app.js",
        "export function app() {\n  return 1;\n}\n",
    )
    _write(clone_root, "README.md", "# docs\n")

    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(indexing_service, "SessionLocal", factory)
    monkeypatch.setattr(settings, "temporary_storage_directory", temporary)
    monkeypatch.setattr(
        indexing_service,
        "clone_repository",
        lambda *args, **kwargs: CloneResult(
            commit_sha="abc123",
            default_branch="main",
            local_path=str(clone_root),
        ),
    )

    indexing_service.run_indexing_job(repository_id, job_id)

    worker_session = factory()
    try:
        repository = worker_session.get(Repository, repository_id)
        job = worker_session.get(IndexingJob, job_id)
        assert repository is not None
        assert job is not None
        assert repository.default_branch == "main"
        assert job.commit_sha == "abc123"
        assert job.files_discovered == 2
        assert job.files_processed == 2
        assert job.total_chunks >= 2
        assert job.status == "succeeded"
        assert job.current_step == "completed"
        assert job.progress == 100
        assert job.error_code is None
        assert repository.status == "ready"
        assert repository.active_index_version == str(job.index_version)
        assert repository.active_commit_sha == "abc123"
        assert repository.indexed_at is not None
        assert repository.last_error is None
    finally:
        worker_session.close()

    manifest = temporary / f"chunks-{repository_id}-{job_id}.jsonl"
    assert manifest.is_file()
    chunks = [
        json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()
    ]
    assert len(chunks) == job.total_chunks
    assert chunks
    assert all(chunk["repository_id"] == str(repository_id) for chunk in chunks)
    assert all(chunk["commit_sha"] == "abc123" for chunk in chunks)
    assert all(chunk["start_line"] >= 1 for chunk in chunks)
    assert all(chunk["end_line"] >= chunk["start_line"] for chunk in chunks)
    assert all(chunk["content_hash"] for chunk in chunks)
    assert {chunk["file_path"] for chunk in chunks} == {
        "src/main.py",
        "src/app.js",
    }

    # Verify ChromaDB has the vectors and they are queryable.
    from app.services.embedding_service import encode_query
    from app.services.vector_store_service import query_chunks

    query_vec = encode_query("how to add two numbers")
    results = query_chunks(repository_id, job.index_version, query_vec, top_k=5)
    assert results
    assert all(r.repository_id == str(repository_id) for r in results)
    assert all(r.score is not None and 0.0 <= r.score <= 1.0 for r in results)

    # Verify count matches.
    from app.services.vector_store_service import count_chunks

    assert count_chunks(repository_id, job.index_version) == job.total_chunks


def test_worker_fails_cleanly_when_no_supported_files_exist(
    db_session,
    test_engine,
    tmp_path,
    monkeypatch,
):
    repository_id, job_id = _create_job(db_session)
    clone_root = tmp_path / "clone"
    _write(clone_root, "README.md", "# docs only\n")

    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(indexing_service, "SessionLocal", factory)
    monkeypatch.setattr(settings, "temporary_storage_directory", tmp_path / "temporary")
    monkeypatch.setattr(
        indexing_service,
        "clone_repository",
        lambda *args, **kwargs: CloneResult(
            commit_sha="abc123",
            default_branch="main",
            local_path=str(clone_root),
        ),
    )

    indexing_service.run_indexing_job(repository_id, job_id)

    worker_session = factory()
    try:
        job = worker_session.get(IndexingJob, job_id)
        assert job is not None
        assert job.error_code == "no_supported_source_files"
    finally:
        worker_session.close()


def test_worker_stops_gracefully_when_repository_deleted_mid_indexing(
    db_session,
    test_engine,
    tmp_path,
    monkeypatch,
):
    """Deleting a repository while indexing runs must not crash the worker.

    The worker should stop processing and leave the job in its current state
    rather than marking it failed or raising an unhandled StaleDataError.
    """
    repository_id, job_id = _create_job(db_session)
    clone_root = tmp_path / "clone"
    _write(clone_root, "src/main.py", "def add(a, b):\n    return a + b\n")

    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(indexing_service, "SessionLocal", factory)
    monkeypatch.setattr(settings, "temporary_storage_directory", tmp_path / "temporary")
    monkeypatch.setattr(
        indexing_service,
        "clone_repository",
        lambda *args, **kwargs: CloneResult(
            commit_sha="abc123",
            default_branch="main",
            local_path=str(clone_root),
        ),
    )

    # Simulate the repository being deleted mid-indexing: the first commit
    # after upserting vectors fails because the job row no longer exists.
    original_safe_commit = indexing_service._safe_commit
    call_count = {"n": 0}

    def failing_safe_commit(db):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            return False
        return original_safe_commit(db)

    monkeypatch.setattr(indexing_service, "_safe_commit", failing_safe_commit)

    # Should not raise.
    indexing_service.run_indexing_job(repository_id, job_id)

    worker_session = factory()
    try:
        job = worker_session.get(IndexingJob, job_id)
        assert job is not None
        # The worker stopped gracefully; it did not mark the job as failed.
        assert job.error_code is None
        assert job.status != "failed"
    finally:
        worker_session.close()
