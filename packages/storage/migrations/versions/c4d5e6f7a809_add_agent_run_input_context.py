"""record immutable Objective and Boundary input context for Agent Runs

Revision ID: c4d5e6f7a809
Revises: b2c3d4e5f607
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a809"
down_revision: str | None = "b2c3d4e5f607"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("input_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "input_context")
