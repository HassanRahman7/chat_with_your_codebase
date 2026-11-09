"""Shared pytest fixtures.

Integration tests use a dedicated PostgreSQL database derived from the
configured application database (or ``TEST_DATABASE_URL``). The production
database is never modified. ``create_all`` is acceptable here because this is an
isolated, disposable test database.
"""

from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.database.models  # noqa: F401 - register metadata
from app.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.services import indexing_service


def _test_database_url():
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        return make_url(override)
    url = make_url(settings.database_url)
    return url.set(database=f"{url.database}_test")


@pytest.fixture(scope="session")
def test_engine():
    url = _test_database_url()
    database_name = url.database or "codebase_ai_test"
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        pytest.skip("Unsafe test database name.")

    admin_url = url.set(database="postgres")
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        admin_engine.dispose()

        engine = create_engine(url, pool_pre_ping=True)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL test database unavailable ({type(exc).__name__}).")

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE messages, conversations, indexing_jobs, "
                    "repositories RESTART IDENTITY CASCADE"
                )
            )


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_get_db():
        yield db_session

    # The API tests exercise request handling, not real network cloning.
    monkeypatch.setattr(
        indexing_service,
        "run_indexing_job",
        lambda repository_id, job_id: None,
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
