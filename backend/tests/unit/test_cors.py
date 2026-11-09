"""CORS configuration tests for local development origins."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


@pytest.mark.parametrize(
    "origin",
    ["http://one.example", "http://two.example"],
)
def test_cors_allows_comma_separated_origins(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
) -> None:
    monkeypatch.setattr(
        settings,
        "frontend_origin",
        "http://one.example, http://two.example",
    )

    client = TestClient(create_app())
    response = client.get("/", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
