"""add Acquisition Mission runs and signal lineage

Revision ID: a1c3e5f7b902
Revises: e7a9c1d3f425
Create Date: 2026-08-02 20:10:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1c3e5f7b902"
down_revision: str | None = "e7a9c1d3f425"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_mission_id_source_config_version_id",
        "acquisition_missions",
        ["id", "source_config_version_id"],
    )
    op.create_table(
        "acquisition_mission_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("source_config_version_id", sa.UUID(), nullable=False),
        sa.Column("replay_of_run_id", sa.UUID(), nullable=True),
        sa.Column("execution_mode", sa.String(length=24), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("budgets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=False),
        sa.Column("context_completeness", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checkpoints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("terminal_state", sa.String(length=24), nullable=False),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("transport_requests", sa.Integer(), nullable=False),
        sa.Column("network_requests", sa.Integer(), nullable=False),
        sa.Column("external_signal_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mission_id", "source_config_version_id"],
            [
                "acquisition_missions.id",
                "acquisition_missions.source_config_version_id",
            ],
            name="fk_run_uses_mission_pinned_config",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replay_of_run_id"],
            ["acquisition_mission_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("retry_count >= 0", name="ck_mission_run_retry_count_nonnegative"),
        sa.CheckConstraint(
            "transport_requests >= 0", name="ck_mission_run_transport_requests_nonnegative"
        ),
        sa.CheckConstraint(
            "network_requests >= 0", name="ck_mission_run_network_requests_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("external_signals", sa.Column("mission_run_id", sa.UUID(), nullable=True))
    op.add_column("external_signals", sa.Column("lineage_key", sa.Text(), nullable=True))
    op.add_column("external_signals", sa.Column("raw_artifact_key", sa.Text(), nullable=True))
    op.add_column(
        "external_signals", sa.Column("parent_context_available", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "external_signals",
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_external_signal_mission_run",
        "external_signals",
        "acquisition_mission_runs",
        ["mission_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_external_signal_lineage_key",
        "external_signals",
        ["lineage_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_external_signal_lineage_key", "external_signals", type_="unique")
    op.drop_constraint("fk_external_signal_mission_run", "external_signals", type_="foreignkey")
    op.drop_column("external_signals", "context_snapshot")
    op.drop_column("external_signals", "parent_context_available")
    op.drop_column("external_signals", "raw_artifact_key")
    op.drop_column("external_signals", "lineage_key")
    op.drop_column("external_signals", "mission_run_id")
    op.drop_table("acquisition_mission_runs")
    op.drop_constraint(
        "uq_mission_id_source_config_version_id",
        "acquisition_missions",
        type_="unique",
    )
