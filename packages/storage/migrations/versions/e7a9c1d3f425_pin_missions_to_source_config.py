"""pin Acquisition Missions to immutable source configuration versions

Revision ID: e7a9c1d3f425
Revises: d4e6f8a0b213
Create Date: 2026-08-02 19:20:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "e7a9c1d3f425"
down_revision: str | None = "d4e6f8a0b213"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acquisition_missions",
        sa.Column("source_config_version_id", sa.UUID(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_source_config_source_id_id",
        "source_config_versions",
        ["source_id", "id"],
    )
    op.create_foreign_key(
        "fk_mission_config_belongs_to_source",
        "acquisition_missions",
        "source_config_versions",
        ["source_id", "source_config_version_id"],
        ["source_id", "id"],
        ondelete="RESTRICT",
    )
    op.execute(
        "ALTER TABLE acquisition_missions "
        "ADD CONSTRAINT ck_acquisition_mission_config_pin_required "
        "CHECK (source_config_version_id IS NOT NULL) NOT VALID"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_acquisition_mission_config_pin_required",
        "acquisition_missions",
        type_="check",
    )
    op.drop_constraint(
        "fk_mission_config_belongs_to_source",
        "acquisition_missions",
        type_="foreignkey",
    )
    op.drop_column("acquisition_missions", "source_config_version_id")
    op.drop_constraint(
        "uq_source_config_source_id_id",
        "source_config_versions",
        type_="unique",
    )
