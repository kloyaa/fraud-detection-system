"""Base SQLAlchemy models for RAS.

Use lazy='raise' on all relationships to prevent N+1 queries.
Always use selectinload() or joinedload() for eager loading.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String, func, Float, Integer
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


class RiskAssessment(TimestampedModel):
    """Risk assessment record for audit trail and analytics.

    Stores all scoring requests and decisions for:
    - Audit compliance (PCI DSS Requirement 10)
    - FCRA adverse action reason tracking
    - Model monitoring and drift detection
    - Performance analytics
    """

    __tablename__ = "risk_assessments"

    # Request context
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Transaction details (denormalized for query efficiency)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    merchant_category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    merchant_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    # Risk decision
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)  # LOW/MEDIUM/HIGH
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVE/DECLINE/REVIEW

    # Reason codes for FCRA adverse action
    reason_codes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # JSON array

    # Scoring metadata
    engine_version: Mapped[Optional[str]] = mapped_column(
        String(50), default="1.0.0", nullable=True
    )
    processing_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Optional: correlation for tracing
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    def __repr__(self) -> str:
        return (
            f"<RiskAssessment("
            f"id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"risk_level={self.risk_level}, "
            f"decision={self.decision}"
            f")>"
        )
