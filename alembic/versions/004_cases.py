"""Add cases table for investigation workflow.

Revision ID: 004_cases
Revises: 003_risk_decisions
Create Date: 2026-03-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "004_cases"
down_revision = "003_risk_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("case_id", sa.String(255), nullable=False),
        sa.Column(
            "decision_id",
            sa.Integer(),
            sa.ForeignKey("risk_decisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("customer_id", sa.String(255), nullable=False),
        sa.Column("merchant_id", sa.String(255), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="P3"),
        sa.Column("assigned_analyst", sa.String(255), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.String(2000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
    )

    op.create_index("ix_cases_case_id", "cases", ["case_id"], unique=True)
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"])
    op.create_index("ix_cases_decision_id", "cases", ["decision_id"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_priority", "cases", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_cases_priority", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_decision_id", table_name="cases")
    op.drop_index("ix_cases_customer_id", table_name="cases")
    op.drop_index("ix_cases_case_id", table_name="cases")
    op.drop_table("cases")
