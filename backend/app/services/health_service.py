"""Dependency health checks used by the health endpoint.

Checks are intentionally shallow: they confirm connectivity only and never
return connection strings, credentials, or driver errors to the client.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.database.session import engine

logger = logging.getLogger(__name__)


def check_postgresql() -> str:
    """Return ``ok`` if a trivial query succeeds, otherwise ``unavailable``."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 - report state, never details
        logger.warning("PostgreSQL health check failed: %s", type(exc).__name__)
        return "unavailable"


def check_chromadb() -> str:
    """Return ``ok`` if the in-memory vector store is available."""
    try:
        # The in-memory vector store is always available once imported.
        from app.services.vector_store_service import _vector_store  # noqa: F401

        return "ok"
    except Exception as exc:  # noqa: BLE001 - report state, never details
        logger.warning("Vector store health check failed: %s", type(exc).__name__)
        return "unavailable"
