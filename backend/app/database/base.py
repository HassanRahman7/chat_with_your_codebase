"""Shared SQLAlchemy declarative base.

Models are registered on this metadata. Alembic imports it to autogenerate
migrations; ``Base.metadata.create_all()`` is intentionally not used as a
migration strategy.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all relational models."""
