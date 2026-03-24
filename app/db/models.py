"""Base SQLAlchemy models for RAS.

Use lazy='raise' on all relationships to prevent N+1 queries.
Always use selectinload() or joinedload() for eager loading.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Provides common columns: id, created_at, updated_at.
    """

    pass


class TimestampedModel(Base):
    """Base model with audit timestamps.

    Extends Base with created_at and updated_at fields that auto-populate.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
