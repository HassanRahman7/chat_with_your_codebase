"""Sentence Transformer embedding service.

Loads the configured embedding model once per process and exposes batched
encoding for code chunks and natural-language queries. BGE-style models are
handled with the recommended ``query: `` prefix for retrieval questions.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings
from app.services.errors import EmbeddingError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    """Load the sentence-transformers model once and cache it."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _get_model():
    try:
        return _load_model(settings.embedding_model)
    except Exception as exc:  # noqa: BLE001 - convert to safe domain error
        logger.exception("Failed to load embedding model %s", settings.embedding_model)
        raise EmbeddingError(
            f"Could not load embedding model {settings.embedding_model}"
        ) from exc


def model_name() -> str:
    """Return the configured embedding model identifier."""
    return settings.embedding_model


def model_dimension() -> int:
    """Return the embedding vector dimension for the configured model."""
    model = _get_model()
    return int(model.get_sentence_embedding_dimension())


def _prefix_for_query(text: str) -> str:
    """BGE recommends a ``query: `` prefix for retrieval questions."""
    if text.startswith("query: "):
        return text
    return f"query: {text}"


def _prefix_for_passage(text: str) -> str:
    """BGE passages are encoded without a prefix by default."""
    return text


def encode_query(text: str) -> list[float]:
    """Encode a natural-language question into a normalized embedding vector."""
    if not text or not text.strip():
        raise EmbeddingError("Question text must not be empty.")
    model = _get_model()
    vector = model.encode(
        [_prefix_for_query(text.strip())],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vector[0].tolist()


def encode_texts(
    texts: list[str], batch_size: int | None = None
) -> list[list[float]]:
    """Encode a list of code-chunk texts into normalized embedding vectors."""
    if not texts:
        return []
    model = _get_model()
    batch = settings.embedding_batch_size if batch_size is None else batch_size
    vectors = model.encode(
        [_prefix_for_passage(t) for t in texts],
        batch_size=batch,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return [vector.tolist() for vector in vectors]


def warm_up() -> None:
    """Eagerly load the embedding model so the first request is not delayed."""
    _get_model()
