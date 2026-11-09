"""SQLAlchemy models for the application database.

Importing this package registers every model on ``Base.metadata`` so Alembic
can autogenerate migrations. The four tables mirror ``Database.md`` exactly:
repositories, indexing jobs, conversations and messages.
"""

from __future__ import annotations

from app.database.models.conversation import Conversation
from app.database.models.indexing_job import IndexingJob
from app.database.models.message import Message
from app.database.models.repository import Repository

__all__ = ["Conversation", "IndexingJob", "Message", "Repository"]
