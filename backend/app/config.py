"""Centralized, typed application configuration.

All runtime configuration is read from environment variables (optionally loaded
from ``backend/.env``). No other module should read ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``backend/`` directory. Storage paths are resolved relative to this so the
# application behaves the same regardless of the current working directory.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed application settings.

    Defaults are safe, documented values for local development. Anything that
    is environment-specific (credentials, origins) is overridable via ``.env``.
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    app_env: str = "development"
    app_name: str = "Codebase AI"
    app_version: str = "0.1.0"
    service_name: str = "chat-with-any-codebase"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # --- Runtime ---------------------------------------------------------
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    # --- Persistence -----------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://postgres:password@localhost:5432/codebase_ai"
    )
    chroma_persist_directory: Path = Path("./storage/chroma")
    repository_storage_directory: Path = Path("./storage/repositories")
    temporary_storage_directory: Path = Path("./storage/temporary")
    chroma_collection_name: str = "code_chunks"

    # --- AI providers ----------------------------------------------------
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_batch_size: int = 32

    # --- Retrieval -------------------------------------------------------
    retrieval_top_k: int = 5
    retrieval_min_relevance: float = 0.2

    # --- Ingestion limits -------------------------------------------------
    max_repository_size_mb: int = 200
    max_file_size_mb: int = 1
    max_repository_files: int = 5000
    clone_timeout_seconds: int = 300
    max_github_url_length: int = 2048

    # --- Request limits ---------------------------------------------------
    max_question_length: int = 4000
    llm_timeout_seconds: int = 60
    chat_timeout_seconds: int = 90

    @field_validator(
        "chroma_persist_directory",
        "repository_storage_directory",
        "temporary_storage_directory",
        mode="after",
    )
    @classmethod
    def _resolve_storage_path(cls, value: Path) -> Path:
        """Resolve relative storage paths against the backend directory."""
        if value.is_absolute():
            return value
        return (BASE_DIR / value).resolve()

    def ensure_storage_directories(self) -> None:
        """Create local storage directories if they do not exist yet."""
        for directory in (
            self.chroma_persist_directory,
            self.repository_storage_directory,
            self.temporary_storage_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


settings = get_settings()
