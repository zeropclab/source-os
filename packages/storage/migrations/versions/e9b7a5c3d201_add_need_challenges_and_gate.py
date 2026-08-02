"""add adversarial Need Issue challenges

Revision ID: e9b7a5c3d201
Revises: c6d4e2f8a701
Create Date: 2026-08-02 21:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e9b7a5c3d201"
down_revision: str | None = "c6d4e2f8a701"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "need_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("falsification_condition", sa.Text(), nullable=False),
        sa.Column("smallest_next_action", sa.Text(), nullable=False),
        sa.Column("assessment", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["need_issue_id"], ["need_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("need_challenges")
