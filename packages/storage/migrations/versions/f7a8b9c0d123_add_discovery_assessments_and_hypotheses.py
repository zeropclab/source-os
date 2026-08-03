"""add discovery assessments and need hypotheses

Revision ID: f7a8b9c0d123
Revises: e6f7a8b9c012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d123"
down_revision: str | None = "e6f7a8b9c012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("assessment_ids", postgresql.JSONB(), nullable=False),
        sa.Column("unknowns", postgresql.JSONB(), nullable=False),
        sa.Column("coverage_gaps", postgresql.JSONB(), nullable=False),
        sa.Column("recommendation", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("objective_id", "version", name="uq_assessment_objective_version"),
    )
    op.create_table(
        "need_hypotheses",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("support_assessment_ids", postgresql.JSONB(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("target_actor", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("desired_outcome", sa.Text(), nullable=False),
        sa.Column("workaround", sa.Text()),
        sa.Column("unknowns", postgresql.JSONB(), nullable=False),
        sa.Column("next_validation_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("promoted_need_issue_id", sa.UUID()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["promoted_need_issue_id"], ["need_issues.id"], ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    op.drop_table("need_hypotheses")
    op.drop_table("discovery_assessments")
