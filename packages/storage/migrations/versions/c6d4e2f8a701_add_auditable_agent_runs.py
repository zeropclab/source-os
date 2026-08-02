"""add auditable bounded Agent Runs

Revision ID: c6d4e2f8a701
Revises: f2a8b4c6d901
Create Date: 2026-08-02 20:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6d4e2f8a701"
down_revision: str | None = "f2a8b4c6d901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("task_instruction", sa.Text(), nullable=False),
        sa.Column("evidence_bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_bundle_hash", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("budgets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tool_allowlist", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tool_audit", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("operator_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_run_idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
