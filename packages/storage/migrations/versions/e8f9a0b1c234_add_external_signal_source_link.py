"""link External Signals to their registered collection source

Revision ID: e8f9a0b1c234
Revises: f1e2d3c4b506
"""

import sqlalchemy as sa
from alembic import op

revision: str = "e8f9a0b1c234"
down_revision: str | None = "f1e2d3c4b506"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("external_signals", sa.Column("source_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_external_signal_source",
        "external_signals",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_external_signal_source", "external_signals", type_="foreignkey")
    op.drop_column("external_signals", "source_id")
