"""add mission run worker leases

Revision ID: a9f3d7b2c814
Revises: f8a2d9c4e116
Create Date: 2026-08-03 08:10:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a9f3d7b2c814"
down_revision: str | None = "f8a2d9c4e116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acquisition_mission_runs",
        sa.Column("execution_attempt", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("acquisition_mission_runs", sa.Column("lease_owner", sa.String(length=100)))
    op.add_column(
        "acquisition_mission_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True))
    )


def downgrade() -> None:
    op.drop_column("acquisition_mission_runs", "lease_expires_at")
    op.drop_column("acquisition_mission_runs", "lease_owner")
    op.drop_column("acquisition_mission_runs", "execution_attempt")
