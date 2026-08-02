"""add source config proposals

Revision ID: c6d7e8f9a122
Revises: b5e6f7a8c011
Create Date: 2026-08-03 04:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6d7e8f9a122"
down_revision: str | None = "b5e6f7a8c011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_config_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_config_version_id", sa.UUID(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("raw_agent_output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_effect", sa.Text(), nullable=False),
        sa.Column("falsification_condition", sa.Text(), nullable=False),
        sa.Column("smallest_verification_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("operator_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_config_version_id"], ["source_config_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_config_proposals")
