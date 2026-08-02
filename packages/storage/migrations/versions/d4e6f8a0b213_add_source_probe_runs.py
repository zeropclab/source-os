"""add bounded source probe runs

Revision ID: d4e6f8a0b213
Revises: c15b6e28f901
Create Date: 2026-08-02 18:30:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e6f8a0b213"
down_revision: str | None = "c15b6e28f901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_probe_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_config_version_id", sa.UUID(), nullable=False),
        sa.Column("request_budget", sa.Integer(), nullable=False),
        sa.Column("time_budget_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("access_state", sa.String(length=24), nullable=False),
        sa.Column("sample_available", sa.Boolean(), nullable=False),
        sa.Column("sample", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pagination_supported", sa.Boolean(), nullable=False),
        sa.Column("replies_supported", sa.Boolean(), nullable=False),
        sa.Column("context_risks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("consumed_requests", sa.Integer(), nullable=False),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False),
        sa.Column("outcome_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_config_version_id"],
            ["source_config_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_probe_runs")
