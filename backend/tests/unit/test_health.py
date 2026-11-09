"""Phase 0 health and error-contract tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import health_service


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health_ok_when_dependencies_ok(monkeypatch, client):
    monkeypatch.setattr(health_service, "check_postgresql", lambda: "ok")
    monkeypatch.setattr(health_service, "check_chromadb", lambda: "ok")

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "chat-with-any-codebase"
    assert body["dependencies"] == {"postgresql": "ok", "chromadb": "ok"}
    assert response.headers["X-Request-ID"].startswith("req_")


def test_health_returns_503_when_dependency_unavailable(monkeypatch, client):
    monkeypatch.setattr(health_service, "check_postgresql", lambda: "unavailable")
    monkeypatch.setattr(health_service, "check_chromadb", lambda: "ok")

    response = client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgresql"] == "unavailable"


def test_unknown_route_uses_standard_error_envelope(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"]
    assert body["error"]["request_id"].startswith("req_")
