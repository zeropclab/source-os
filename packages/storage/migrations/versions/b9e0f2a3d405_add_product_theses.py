"""add product theses and offer observations

Revision ID: b9e0f2a3d405
Revises: a8d9e1f2c304
Create Date: 2026-08-02 23:15:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b9e0f2a3d405"
down_revision: str | None = "a8d9e1f2c304"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_theses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("need_issue_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("user", sa.Text(), nullable=False),
        sa.Column("beneficiary", sa.Text(), nullable=False),
        sa.Column("decision_maker", sa.Text(), nullable=False),
        sa.Column("payer", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("promised_outcome", sa.Text(), nullable=False),
        sa.Column("alternative", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("delivery_mechanism", sa.Text(), nullable=False),
        sa.Column("delivery_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("decision_rationale", sa.Text(), nullable=True),
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
    op.create_table(
        "product_thesis_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_thesis_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("operator_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_thesis_id"], ["product_theses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("product_thesis_observations")
    op.drop_table("product_theses")
