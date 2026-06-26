"""consent_events: append-only, purpose-scoped consent stream (P0 consent gate)

A new tenant-scoped, RLS, APPEND-ONLY table. One purpose per row; a grant or an attributable
withdrawal is a NEW row (recompute/withdraw = new event), mirroring the 0003/0007 append-only
pattern. The legacy mutable `consent_records` table is left untouched (inert, read by nothing) —
this migration is purely additive and reversible. The patient-facing report-release path is gated
on the latest event for purpose='report_release' (enforced in the service layer).

Revision ID: 0008_consent_events
Revises: 0007_derived_observations
Create Date: 2026-06-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_consent_events"
down_revision: str | None = "0007_derived_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

_PURPOSES = ("report_release", "analytics", "data_source_connect")
_EVENT_TYPES = ("granted", "withdrawn")


def upgrade() -> None:
    op.create_table(
        "consent_events",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(*_PURPOSES, native_enum=False, length=40, name="consent_purpose"),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(*_EVENT_TYPES, native_enum=False, length=40, name="consent_event_type"),
            nullable=False,
        ),
        sa.Column("consent_text_version", sa.String(length=40), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_consent_events_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_consent_events_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name=op.f("fk_consent_events_recorded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_events")),
    )
    op.create_index(
        "ix_consent_events_patient_purpose", "consent_events", ["patient_id", "purpose"]
    )
    op.create_index(op.f("ix_consent_events_tenant_id"), "consent_events", ["tenant_id"])

    # Grants + RLS (ENABLE + FORCE + one ALL policy), mirroring 0007.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON consent_events TO hadp_app")
    op.execute("ALTER TABLE consent_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE consent_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON consent_events "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )

    # Append-only: a withdrawal is a NEW event; rows are never updated or deleted.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_consent_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON consent_events FROM hadp_app")
    op.execute(
        "CREATE TRIGGER consent_events_append_only "
        "BEFORE UPDATE OR DELETE ON consent_events "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_consent_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS consent_events_append_only ON consent_events")
    op.execute("DROP FUNCTION IF EXISTS hadp_block_consent_mutation()")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON consent_events")
    op.execute("ALTER TABLE consent_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE consent_events DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_consent_events_tenant_id"), table_name="consent_events")
    op.drop_index("ix_consent_events_patient_purpose", table_name="consent_events")
    op.drop_table("consent_events")
