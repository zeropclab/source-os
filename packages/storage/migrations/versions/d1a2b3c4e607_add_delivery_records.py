"""add delivery evidence records

Revision ID: d1a2b3c4e607
Revises: c0f1a2b3d506
Create Date: 2026-08-03 00:05:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "d1a2b3c4e607"
down_revision: str | None = "c0f1a2b3d506"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feature_definition_id", sa.UUID(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=False),
        sa.Column("implementation_version", sa.String(length=64), nullable=False),
        sa.Column("tests_evidence", sa.Text(), nullable=True),
        sa.Column("review_conclusion", sa.Text(), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("migration_evidence", sa.Text(), nullable=True),
        sa.Column("rollback_evidence", sa.Text(), nullable=True),
        sa.Column("acceptance_evidence", sa.Text(), nullable=True),
        sa.Column("tracking_evidence", sa.Text(), nullable=True),
        sa.Column("pr_reference", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["feature_definition_id"], ["feature_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("delivery_records")
