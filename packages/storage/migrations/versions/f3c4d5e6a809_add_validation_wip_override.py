"""add validation work-in-progress override audit

Revision ID: f3c4d5e6a809
Revises: e2b3c4d5f708
Create Date: 2026-08-03 00:45:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f3c4d5e6a809"
down_revision: str | None = "e2b3c4d5f708"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validation_experiments", sa.Column("wip_override_reason", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("validation_experiments", "wip_override_reason")
