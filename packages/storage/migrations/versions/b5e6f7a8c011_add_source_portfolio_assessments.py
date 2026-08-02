"""add source portfolio assessments

Revision ID: b5e6f7a8c011
Revises: a4d5e6f7b910
Create Date: 2026-08-03 02:20:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b5e6f7a8c011"
down_revision: str | None = "a4d5e6f7b910"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_portfolio_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=128), nullable=False),
        sa.Column("evidence_type", sa.String(length=128), nullable=False),
        sa.Column("portfolio_mode", sa.String(length=16), nullable=False),
        sa.Column("technical_success_rate", sa.Float(), nullable=False),
        sa.Column("context_completeness_rate", sa.Float(), nullable=False),
        sa.Column("evidence_usefulness_rate", sa.Float(), nullable=False),
        sa.Column("independent_evidence_count", sa.Integer(), nullable=False),
        sa.Column("counterevidence_count", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_cents", sa.Integer(), nullable=False),
        sa.Column("downstream_decision_impact", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_portfolio_assessments")
