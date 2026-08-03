"""add validation execution tasks

Revision ID: b1c2d3e4f506
Revises: a9f3d7b2c814
Create Date: 2026-08-03 09:15:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f506"
down_revision: str | None = "a9f3d7b2c814"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_execution_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("target_label", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("contact_reference", sa.Text(), nullable=False),
        sa.Column("outreach_script", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="planned"),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
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
    op.drop_table("validation_execution_tasks")
