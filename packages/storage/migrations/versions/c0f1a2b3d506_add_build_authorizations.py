"""add build authorization and traceable feature fields

Revision ID: c0f1a2b3d506
Revises: b9e0f2a3d405
Create Date: 2026-08-02 23:40:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c0f1a2b3d506"
down_revision: str | None = "b9e0f2a3d405"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "build_authorizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_thesis_id", sa.UUID(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_thesis_id"], ["product_theses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_thesis_id"),
    )
    op.add_column("feature_definitions", sa.Column("product_thesis_id", sa.UUID(), nullable=True))
    op.add_column(
        "feature_definitions",
        sa.Column("explicit_exclusions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("feature_definitions", sa.Column("rollback_condition", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_feature_definition_product_thesis",
        "feature_definitions",
        "product_theses",
        ["product_thesis_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_feature_definition_product_thesis", "feature_definitions", type_="foreignkey"
    )
    op.drop_column("feature_definitions", "rollback_condition")
    op.drop_column("feature_definitions", "explicit_exclusions")
    op.drop_column("feature_definitions", "product_thesis_id")
    op.drop_table("build_authorizations")
