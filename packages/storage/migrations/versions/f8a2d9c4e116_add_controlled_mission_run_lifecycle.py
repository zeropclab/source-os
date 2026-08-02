"""add controlled acquisition mission run lifecycle

Revision ID: f8a2d9c4e116
Revises: c6d7e8f9a122
Create Date: 2026-08-03 07:10:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f8a2d9c4e116"
down_revision: str | None = "c6d7e8f9a122"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acquisition_mission_runs",
        sa.Column(
            "lifecycle_status",
            sa.String(length=24),
            server_default="completed",
            nullable=False,
        ),
    )
    op.add_column("acquisition_mission_runs", sa.Column("control_reason", sa.Text(), nullable=True))
    op.alter_column("acquisition_mission_runs", "completed_at", nullable=True)


def downgrade() -> None:
    op.alter_column(
        "acquisition_mission_runs", "completed_at", nullable=False, server_default=sa.text("now()")
    )
    op.drop_column("acquisition_mission_runs", "control_reason")
    op.drop_column("acquisition_mission_runs", "lifecycle_status")
