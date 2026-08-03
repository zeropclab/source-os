"""add operator approvals and boundary revisions

Revision ID: d5e6f7a8b901
Revises: c3d4e5f6a708
Create Date: 2026-08-03 16:35:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b901"
down_revision: str | None = "c3d4e5f6a708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovery_objectives", sa.Column("block_reason", sa.Text(), nullable=True))
    op.add_column(
        "approved_collection_boundaries",
        sa.Column(
            "credential_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "approved_collection_boundaries",
        sa.Column(
            "evidence_conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_table(
        "operator_approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("request_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "requested_boundary_patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("operator", sa.String(length=120), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "operator_boundary_revisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("boundary_id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("operator", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("boundary_patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["boundary_id"], ["approved_collection_boundaries.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["approval_id"], ["operator_approvals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_id"),
    )


def downgrade() -> None:
    op.drop_table("operator_boundary_revisions")
    op.drop_table("operator_approvals")
    op.drop_column("approved_collection_boundaries", "evidence_conditions")
    op.drop_column("approved_collection_boundaries", "credential_scope")
    op.drop_column("discovery_objectives", "block_reason")
