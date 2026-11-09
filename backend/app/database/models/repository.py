"""Repository model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    desc,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.conversation import Conversation
    from app.database.models.indexing_job import IndexingJob


REPOSITORY_STATUSES = (
    "pending",
    "cloning",
    "indexing",
    "ready",
    "failed",
    "updating",
    "deleting",
)


class Repository(Base):
    """One registered GitHub repository."""

    __tablename__ = "repositories"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'cloning', 'indexing', 'ready', "
            "'failed', 'updating', 'deleting')",
            name="ck_repositories_status",
        ),
        CheckConstraint(
            "(active_commit_sha IS NULL) = (active_index_version IS NULL)",
            name="ck_repositories_active_index_pair",
        ),
        UniqueConstraint("github_url", name="uq_repositories_github_url"),
        Index("ix_repositories_status_created_at", "status", desc("created_at")),
        Index("ix_repositories_updated_at", desc("updated_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str | None] = mapped_column(String(255))
    default_branch: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default=text("'pending'")
    )
    active_commit_sha: Mapped[str | None] = mapped_column(String(64))
    active_index_version: Mapped[str | None] = mapped_column(String(128))
    local_path: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Repository id={self.id} name={self.repository_name!r}>"
