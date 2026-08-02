"""add immutable external signal evidence spine

Revision ID: b84e1a78d2c1
Revises: 92cf6e1b4a27
Create Date: 2026-08-02 15:10:00
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b84e1a78d2c1"
down_revision: str | None = "92cf6e1b4a27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("original_material", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "signal_triage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("signal_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["external_signals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_signals_status_captured_at",
        "external_signals",
        ["status", "captured_at"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_external_signal_content_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.source_label IS DISTINCT FROM OLD.source_label
                OR NEW.source_uri IS DISTINCT FROM OLD.source_uri
                OR NEW.original_material IS DISTINCT FROM OLD.original_material
                OR NEW.observed_at IS DISTINCT FROM OLD.observed_at
                OR NEW.observation IS DISTINCT FROM OLD.observation
                OR NEW.interpretation IS DISTINCT FROM OLD.interpretation THEN
                RAISE EXCEPTION 'External signal provenance and content are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """

        CREATE TRIGGER external_signal_content_immutable
        BEFORE UPDATE ON external_signals
        FOR EACH ROW EXECUTE FUNCTION prevent_external_signal_content_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_external_signal_deletion()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'External signals cannot be deleted from the evidence spine';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER external_signal_immutable
        BEFORE DELETE ON external_signals
        FOR EACH ROW EXECUTE FUNCTION prevent_external_signal_deletion();
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_signal_triage_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Signal triage events are immutable audit records';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER signal_triage_event_immutable
        BEFORE UPDATE OR DELETE ON signal_triage_events
        FOR EACH ROW EXECUTE FUNCTION prevent_signal_triage_event_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER signal_triage_event_immutable ON signal_triage_events")
    op.execute("DROP FUNCTION prevent_signal_triage_event_mutation()")
    op.execute("DROP TRIGGER external_signal_immutable ON external_signals")
    op.execute("DROP FUNCTION prevent_external_signal_deletion()")
    op.execute("DROP TRIGGER external_signal_content_immutable ON external_signals")
    op.execute("DROP FUNCTION prevent_external_signal_content_mutation()")
    op.drop_index("ix_external_signals_status_captured_at", table_name="external_signals")
    op.drop_table("signal_triage_events")
    op.drop_table("external_signals")
