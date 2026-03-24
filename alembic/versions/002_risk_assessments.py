"""Add risk_assessments table for audit trail.

Revision ID: 002_risk_assessments
Revises: 001_initial
Create Date: 2026-03-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_risk_assessments"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create risk_assessments table for scoring audit trail."""
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("transaction_id", sa.String(255), nullable=False),
        sa.Column("customer_id", sa.String(255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("merchant_category", sa.String(255), nullable=True),
        sa.Column("merchant_country", sa.String(2), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("reason_codes", sa.String(1000), nullable=True),
        sa.Column("engine_version", sa.String(50), server_default="1.0.0"),
        sa.Column("processing_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for fast lookups
    op.create_index("ix_risk_assessments_idempotency_key", "risk_assessments", ["idempotency_key"])
    op.create_index("ix_risk_assessments_transaction_id", "risk_assessments", ["transaction_id"])
    op.create_index("ix_risk_assessments_customer_id", "risk_assessments", ["customer_id"])
    op.create_index("ix_risk_assessments_request_id", "risk_assessments", ["request_id"])
    op.create_index("ix_risk_assessments_created_at", "risk_assessments", ["created_at"])


def downgrade() -> None:
    """Drop risk_assessments table and related indexes."""
    op.drop_index("ix_risk_assessments_created_at", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_request_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_customer_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_transaction_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_idempotency_key", table_name="risk_assessments")
    op.drop_table("risk_assessments")
