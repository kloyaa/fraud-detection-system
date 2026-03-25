"""Base SQLAlchemy models for RAS.

Use lazy='raise' on all relationships to prevent N+1 queries.
Always use selectinload() or joinedload() for eager loading.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
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


class RiskDecision(TimestampedModel):
    """Risk decision record aligned with the Kafka risk.decisions Avro schema.

    Written after the scoring pipeline completes. This is the canonical record
    for analytics queries, downstream Flink consumers, and case triggers.
    """

    __tablename__ = "risk_decisions"

    # Trace context
    request_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Entity identifiers
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Transaction details
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Scoring result (0–1000 integer for Kafka Avro compat; 0.0–1.0 float in risk_assessments)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVE/REVIEW/DECLINE
    rules_triggered: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # JSON array

    # Engine metadata
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="rule-only-v1")
    processing_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False, default="us-east-1")
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    # Kafka delivery tracking
    published_to_kafka: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kafka_offset: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RiskDecision("
            f"id={self.id}, "
            f"request_id={self.request_id}, "
            f"decision={self.decision}"
            f")>"
        )


class Case(TimestampedModel):
    """Investigation case created when a transaction exceeds the case-creation threshold.

    Cases are created by the case-trigger consumer (risk.decisions topic)
    when score > 600 or compliance flags are present (per kafka_topics.md).
    """

    __tablename__ = "cases"

    # External identifier (UUID, shared with case management UI)
    case_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Link to the decision that triggered this case
    decision_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("risk_decisions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Entity context (denormalized for query efficiency)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Case lifecycle
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P3")  # P1/P2/P3
    assigned_analyst: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Resolution
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Case("
            f"id={self.id}, "
            f"case_id={self.case_id}, "
            f"status={self.status}, "
            f"priority={self.priority}"
            f")>"
        )


class Rule(TimestampedModel):
    """Fraud detection rule stored in PostgreSQL (authoritative rule store per ADR-008).

    The rule engine reads active rules at startup and on rules.changed Kafka events.
    The Kafka message is a notification pointer; PostgreSQL holds the full definition.
    """

    __tablename__ = "rules"

    # Rule identity
    rule_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # Rule logic (JSON-serialised condition expression)
    condition: Mapped[str] = mapped_column(String(4000), nullable=False)
    score_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # FLAG/BLOCK/ALLOW

    # Lifecycle
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Rule("
            f"id={self.id}, "
            f"rule_id={self.rule_id}, "
            f"name={self.name}, "
            f"enabled={self.enabled}"
            f")>"
        )
