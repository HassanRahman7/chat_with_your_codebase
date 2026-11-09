"""Health router."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.config import settings
from app.schemas.health import HealthResponse
from app.services import health_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and dependency health",
    description=(
        "Reports process health plus controlled PostgreSQL and ChromaDB "
        "connectivity checks. Returns 503 when a required dependency is "
        "unavailable."
    ),
    responses={503: {"model": HealthResponse}},
)
def health(response: Response) -> HealthResponse:
    dependencies = {
        "postgresql": health_service.check_postgresql(),
        "chromadb": health_service.check_chromadb(),
    }
    healthy = all(state == "ok" for state in dependencies.values())
    response.status_code = 200 if healthy else 503
    return HealthResponse(
        status="ok" if healthy else "degraded",
        service=settings.service_name,
        version=settings.app_version,
        dependencies=dependencies,
    )
