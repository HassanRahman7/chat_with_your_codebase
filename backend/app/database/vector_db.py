"""ChromaDB client adapter.

ChromaDB access is centralized here. Routers, parsers and RAG prompt code must
not create their own clients.
"""

from __future__ import annotations

import logging
import threading

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def get_chroma_client():
    """Return a lazily created, process-wide persistent ChromaDB client."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                import chromadb

                settings.ensure_storage_directories()
                _client = chromadb.PersistentClient(
                    path=str(settings.chroma_persist_directory)
                )
                logger.info(
                    "ChromaDB persistent client initialized at %s",
                    settings.chroma_persist_directory,
                )
    return _client


def reset_chroma_client() -> None:
    """Drop the cached client. Used by tests and re-indexing tooling."""
    global _client
    with _client_lock:
        _client = None
