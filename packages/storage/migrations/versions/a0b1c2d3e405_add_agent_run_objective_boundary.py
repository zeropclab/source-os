"""link Agent Runs to immutable Discovery Objective boundaries

Revision ID: a0b1c2d3e405
Revises: f7a8b9c0d123
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e405"
down_revision: str | None = "f7a8b9c0d123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("objective_id", sa.UUID(), nullable=True))
    op.add_column("agent_runs", sa.Column("boundary_id", sa.UUID(), nullable=True))
    op.add_column("agent_runs", sa.Column("boundary_version", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_agent_run_objective",
        "agent_runs",
        "discovery_objectives",
        ["objective_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_agent_run_boundary",
        "agent_runs",
        "approved_collection_boundaries",
        ["boundary_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_run_boundary", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_run_objective", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "boundary_version")
    op.drop_column("agent_runs", "boundary_id")
    op.drop_column("agent_runs", "objective_id")
