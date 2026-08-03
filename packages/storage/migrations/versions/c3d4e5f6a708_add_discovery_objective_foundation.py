"""add Discovery Objective foundation

Revision ID: c3d4e5f6a708
Revises: b1c2d3e4f506
Create Date: 2026-08-03 16:10:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a708"
down_revision: str | None = "b1c2d3e4f506"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_objectives",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "resource_stop_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "evidence_stop_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "decision_stop_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "approved_collection_boundaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tool_allowlist", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=False),
        sa.Column("time_budget_minutes", sa.Integer(), nullable=False),
        sa.Column("cost_budget_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("objective_id", "version", name="uq_boundary_objective_version"),
    )


def downgrade() -> None:
    op.drop_table("approved_collection_boundaries")
    op.drop_table("discovery_objectives")
