"""Indexing job model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
    desc,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.repository import Repository


class IndexingJob(Base):
    """One indexing attempt for a repository."""

    __tablename__ = "indexing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_indexing_jobs_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_indexing_jobs_progress_range",
        ),
        CheckConstraint(
            "files_discovered >= 0 AND files_processed >= 0 AND total_chunks >= 0",
            name="ck_indexing_jobs_non_negative_counters",
        ),
        Index(
            "ix_indexing_jobs_repository_created_at",
            "repository_id",
            desc("created_at"),
        ),
        Index("ix_indexing_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", server_default=text("'queued'")
    )
    current_step: Mapped[str | None] = mapped_column(String(64))
    progress: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    files_discovered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    files_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    total_chunks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    index_version: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    repository: Mapped["Repository"] = relationship(back_populates="indexing_jobs")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<IndexingJob id={self.id} status={self.status!r}>"
