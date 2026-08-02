"""add immutable source configuration versions

Revision ID: c15b6e28f901
Revises: 7b2d3e4f5a61
Create Date: 2026-08-02 16:10:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c15b6e28f901"
down_revision: str | None = "7b2d3e4f5a61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_config_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("access_mode", sa.String(length=24), nullable=False),
        sa.Column("query_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "pagination_context_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("extraction_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "version"),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_source_config_version_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Source configuration versions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER source_config_version_immutable
        BEFORE UPDATE OR DELETE ON source_config_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_source_config_version_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER source_config_version_immutable ON source_config_versions")
    op.execute("DROP FUNCTION prevent_source_config_version_mutation()")
    op.drop_table("source_config_versions")
