"""add evidence-backed Need Issue workflow

Revision ID: 92cf6e1b4a27
Revises: 5f727ef2d93d
Create Date: 2026-08-01 23:35:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "92cf6e1b4a27"
down_revision: str | None = "5f727ef2d93d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "need_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("target_actor", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("desired_outcome", sa.Text(), nullable=False),
        sa.Column("workaround", sa.Text(), nullable=True),
        sa.Column("counterevidence_summary", sa.Text(), nullable=True),
        sa.Column("next_validation_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        "need_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=False),
        sa.Column("reference_uri", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["need_issue_id"], ["need_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "feature_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("user_task", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tracking_events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tracking_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("success_metric", sa.Text(), nullable=False),
        sa.Column("negative_metric", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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


def downgrade() -> None:
    op.drop_table("feature_definitions")
    op.drop_table("need_evidence")
    op.drop_table("need_issues")
