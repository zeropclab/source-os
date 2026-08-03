"""add Acquisition Plans linked to Discovery Objectives

Revision ID: e6f7a8b9c012
Revises: d5e6f7a8b901
Create Date: 2026-08-03 17:05:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c012"
down_revision: str | None = "d5e6f7a8b901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("boundary_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("selected_source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("counterevidence_target", sa.Text(), nullable=False),
        sa.Column("request_budget", sa.Integer(), nullable=False),
        sa.Column("time_budget_minutes", sa.Integer(), nullable=False),
        sa.Column("cost_budget_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["boundary_id"], ["approved_collection_boundaries.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["discovery_objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("objective_id", "version", name="uq_plan_objective_version"),
    )
    op.create_table(
        "plan_revisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("predecessor_plan_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("delta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["acquisition_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["predecessor_plan_id"], ["acquisition_plans.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", name="uq_plan_revision_plan"),
    )
    op.add_column(
        "acquisition_missions",
        sa.Column("acquisition_plan_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_mission_acquisition_plan",
        "acquisition_missions",
        "acquisition_plans",
        ["acquisition_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_mission_acquisition_plan", "acquisition_missions", type_="foreignkey")
    op.drop_column("acquisition_missions", "acquisition_plan_id")
    op.drop_table("plan_revisions")
    op.drop_table("acquisition_plans")
