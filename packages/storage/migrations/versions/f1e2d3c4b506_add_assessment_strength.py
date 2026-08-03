"""add assessed evidence strength to Discovery Assessments

Revision ID: f1e2d3c4b506
Revises: d6e7f8a9b012
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f1e2d3c4b506"
down_revision: str | None = "d6e7f8a9b012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovery_assessments",
        sa.Column(
            "evidence_strength",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )


def downgrade() -> None:
    op.drop_column("discovery_assessments", "evidence_strength")
