"""FastAPI application entry point.

Routers stay thin; business logic lives in ``app.services``. Indexing, RAG,
ChromaDB and Gemini access are intentionally absent from this module.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.middleware import RequestIDMiddleware
from app.api.routers import health, indexing, repositories
from app.config import settings
from app.utils.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    settings.ensure_storage_directories()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Repository-aware retrieval and explanation API. "
            "Every answer is grounded in indexed source code."
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.frontend_origin.split(",")
            if origin.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    # Added last so it is the outermost middleware and always sets the ID.
    application.add_middleware(RequestIDMiddleware)

    register_exception_handlers(application)
    application.include_router(health.router, prefix=settings.api_prefix)
    application.include_router(repositories.router, prefix=settings.api_prefix)
    application.include_router(indexing.router, prefix=settings.api_prefix)

    @application.get("/", include_in_schema=False)
    def service_root() -> dict[str, str]:
        return {
            "service": settings.service_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return application


app = create_app()
