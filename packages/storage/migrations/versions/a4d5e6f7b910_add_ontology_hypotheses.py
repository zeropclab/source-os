"""add ontology hypotheses

Revision ID: a4d5e6f7b910
Revises: e2b3c4d5f708
Create Date: 2026-08-03 01:05:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4d5e6f7b910"
down_revision: str | None = "e2b3c4d5f708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ontology_hypotheses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("relationship_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_material", sa.Text(), nullable=False),
        sa.Column("counterexample", sa.Text(), nullable=False),
        sa.Column("unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("smallest_validation_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ontology_hypotheses")
