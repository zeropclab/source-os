"""add validation experiments and market observations

Revision ID: a8d9e1f2c304
Revises: e9b7a5c3d201
Create Date: 2026-08-02 22:30:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a8d9e1f2c304"
down_revision: str | None = "e9b7a5c3d201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_experiments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("budget_cents", sa.Integer(), nullable=False),
        sa.Column("time_limit_hours", sa.Integer(), nullable=False),
        sa.Column("success_threshold", sa.Text(), nullable=False),
        sa.Column("negative_threshold", sa.Text(), nullable=False),
        sa.Column("stop_condition", sa.Text(), nullable=False),
        sa.Column("requires_external_action", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("decision_rationale", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["need_issue_id"], ["need_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "market_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["validation_experiments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("market_observations")
    op.drop_table("validation_experiments")
