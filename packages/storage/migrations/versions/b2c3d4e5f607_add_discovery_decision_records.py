"""add immutable Discovery Decision Records and append-only outcome feedback

Revision ID: b2c3d4e5f607
Revises: a0b1c2d3e405
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f607"
down_revision: str | None = "a0b1c2d3e405"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_decision_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "support_assessment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "counter_assessment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resource_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("objective_id"),
    )
    op.create_table(
        "outcome_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_record_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["decision_record_id"], ["discovery_decision_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("outcome_feedback")
    op.drop_table("discovery_decision_records")
