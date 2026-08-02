"""add feature outcomes and decisions

Revision ID: e2b3c4d5f708
Revises: d1a2b3c4e607
Create Date: 2026-08-03 00:25:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e2b3c4d5f708"
down_revision: str | None = "d1a2b3c4e607"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_outcomes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("delivery_record_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("operator_minutes", sa.Integer(), nullable=True),
        sa.Column("cost_category", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["delivery_record_id"], ["delivery_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "outcome_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("delivery_record_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("threshold_comparison", sa.Text(), nullable=False),
        sa.Column("contribution_margin_cents", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["delivery_record_id"], ["delivery_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_record_id"),
    )


def downgrade() -> None:
    op.drop_table("outcome_decisions")
    op.drop_table("feature_outcomes")
