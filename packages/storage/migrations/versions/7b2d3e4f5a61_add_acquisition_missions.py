"""add bounded Acquisition Mission drafts

Revision ID: 7b2d3e4f5a61
Revises: b84e1a78d2c1
Create Date: 2026-08-02 15:30:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b2d3e4f5a61"
down_revision: str | None = "b84e1a78d2c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_missions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("reality_question", sa.Text(), nullable=False),
        sa.Column("mission_type", sa.String(length=32), nullable=False),
        sa.Column("regions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("query_seeds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("time_budget_minutes", sa.Integer(), nullable=False),
        sa.Column("item_limit", sa.Integer(), nullable=False),
        sa.Column("cost_budget_cents", sa.Integer(), nullable=False),
        sa.Column("stop_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("acquisition_missions")
