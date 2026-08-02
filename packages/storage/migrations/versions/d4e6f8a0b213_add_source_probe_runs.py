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
        sa.Column("pagination_supported", sa.Boolean(), nullable=True),
        sa.Column("replies_supported", sa.Boolean(), nullable=True),
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
        sa.CheckConstraint("request_budget > 0", name="ck_probe_request_budget_positive"),
        sa.CheckConstraint("time_budget_seconds > 0", name="ck_probe_time_budget_positive"),
        sa.CheckConstraint("consumed_requests >= 0", name="ck_probe_consumed_requests_nonnegative"),
        sa.CheckConstraint(
            "consumed_requests <= request_budget", name="ck_probe_consumed_within_budget"
        ),
        sa.CheckConstraint("elapsed_ms >= 0", name="ck_probe_elapsed_nonnegative"),
        sa.CheckConstraint(
            "status IN ('succeeded', 'empty', 'failed')", name="ck_probe_status_valid"
        ),
        sa.CheckConstraint(
            "access_state IN ('public', 'credentialed', 'subscription', 'rate_limited', "
            "'blocked', 'unsupported')",
            name="ck_probe_access_state_valid",
        ),
        sa.CheckConstraint(
            "sample_available = (sample IS NOT NULL)", name="ck_probe_sample_flag_consistent"
        ),
        sa.CheckConstraint(
            "status <> 'succeeded' OR sample_available", name="ck_probe_success_has_sample"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_probe_runs")
