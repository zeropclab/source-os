"""add Need Issue evidence lifecycle and definition history

Revision ID: f2a8b4c6d901
Revises: a1c3e5f7b902
Create Date: 2026-08-02 19:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a8b4c6d901"
down_revision: str | None = "a1c3e5f7b902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "need_issues",
        sa.Column(
            "unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
    )
    op.add_column(
        "need_issues",
        sa.Column("definition_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("need_evidence", sa.Column("external_signal_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_need_evidence_external_signal",
        "need_evidence",
        "external_signals",
        ["external_signal_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "need_issue_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["need_issue_id"], ["need_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("need_issue_id", "version", name="uq_need_issue_version"),
    )
    op.create_table(
        "need_issue_status_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
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
    op.drop_table("need_issue_status_events")
    op.drop_table("need_issue_versions")
    op.drop_constraint("fk_need_evidence_external_signal", "need_evidence", type_="foreignkey")
    op.drop_column("need_evidence", "external_signal_id")
    op.drop_column("need_issues", "definition_version")
    op.drop_column("need_issues", "unknowns")
