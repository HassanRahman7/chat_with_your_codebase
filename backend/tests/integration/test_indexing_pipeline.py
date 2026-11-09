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
        assert job.current_step == "generating_embeddings"
        assert job.error_code == "embedding_pipeline_pending"
        assert job.error_message
        assert job.progress == 80
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
