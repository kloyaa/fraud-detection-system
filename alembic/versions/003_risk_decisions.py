"""Add risk_decisions table aligned with Kafka Avro schema.

Revision ID: 003_risk_decisions
Revises: 002_risk_assessments
Create Date: 2026-03-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "003_risk_decisions"
down_revision = "002_risk_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(255), nullable=False),
        sa.Column("customer_id", sa.String(255), nullable=False),
        sa.Column("merchant_id", sa.String(255), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("rules_triggered", sa.String(1000), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="rule-only-v1"),
        sa.Column("processing_ms", sa.Integer(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("region", sa.String(50), nullable=False, server_default="us-east-1"),
        sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("published_to_kafka", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("kafka_offset", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )

    op.create_index("ix_risk_decisions_request_id", "risk_decisions", ["request_id"], unique=True)
    op.create_index("ix_risk_decisions_customer_id", "risk_decisions", ["customer_id"])
    op.create_index("ix_risk_decisions_created_at", "risk_decisions", ["created_at"])
    op.create_index("ix_risk_decisions_decision", "risk_decisions", ["decision"])


def downgrade() -> None:
    op.drop_index("ix_risk_decisions_decision", table_name="risk_decisions")
    op.drop_index("ix_risk_decisions_created_at", table_name="risk_decisions")
    op.drop_index("ix_risk_decisions_customer_id", table_name="risk_decisions")
    op.drop_index("ix_risk_decisions_request_id", table_name="risk_decisions")
    op.drop_table("risk_decisions")
