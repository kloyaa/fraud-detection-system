"""Add rules table — authoritative rule store (ADR-008).

Revision ID: 005_rules
Revises: 004_cases
Create Date: 2026-03-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "005_rules"
down_revision = "004_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("condition", sa.String(4000), nullable=False),
        sa.Column("score_modifier", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
    )

    op.create_index("ix_rules_rule_id", "rules", ["rule_id"], unique=True)
    op.create_index("ix_rules_enabled", "rules", ["enabled"])


def downgrade() -> None:
    op.drop_index("ix_rules_enabled", table_name="rules")
    op.drop_index("ix_rules_rule_id", table_name="rules")
    op.drop_table("rules")
