"""link Agent Runs to the Plan they are allowed to assess or revise

Revision ID: d6e7f8a9b012
Revises: c4d5e6f7a809
"""

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b012"
down_revision: str | None = "c4d5e6f7a809"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("acquisition_plan_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_agent_run_plan",
        "agent_runs",
        "acquisition_plans",
        ["acquisition_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_run_plan", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "acquisition_plan_id")
