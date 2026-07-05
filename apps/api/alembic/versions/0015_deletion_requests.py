"""Patient-erasure request workflow (docs/notes/0012) — additive, non-destructive.

Adds the `deletion_requests` table (the two-person authorization record for erasing a
patient) and a nullable `patients.erased_at` marker (set when a request is executed — the
execution engine and its append-only-redaction machinery are a SEPARATE later migration).

This migration is deliberately additive and touches NO immutability machinery: it does not
alter the append-only triggers or REVOKEs on consent_events / audit_events / the
interpretation tables. It only creates a new tenant-scoped, RLS-protected table (same
posture as patient_invitations: ENABLE + FORCE RLS, tenant predicate, FKs ON DELETE
RESTRICT) and one nullable column.

`deletion_requests.status` / `reason_category` are closed vocabularies, DB-enforced with
CHECK constraints (doctrine: vocabularies are closed), mirroring migration 0014. A partial
unique index enforces at most one NON-TERMINAL request (pending/approved) per patient.

Revision ID: 0015_deletion_requests
Revises: 0014_enum_check_constraints
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015_deletion_requests"
down_revision = "0014_enum_check_constraints"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

_STATUS_VALUES = ["pending", "approved", "rejected", "cancelled", "executed"]
_REASON_VALUES = ["patient_request", "withdrawn_consent", "data_minimization"]


def upgrade() -> None:
    op.create_table(
        "deletion_requests",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(*_STATUS_VALUES, name="deletionrequeststatus", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column(
            "reason_category",
            sa.Enum(*_REASON_VALUES, name="deletionreasoncategory", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "decided_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "executed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erasure_manifest", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # DB-enforced closed vocabularies (naming convention → ck_deletion_requests_<column>).
    op.create_check_constraint(
        "status",
        "deletion_requests",
        "status IN ('pending', 'approved', 'rejected', 'cancelled', 'executed')",
    )
    op.create_check_constraint(
        "reason_category",
        "deletion_requests",
        "reason_category IN ('patient_request', 'withdrawn_consent', 'data_minimization')",
    )
    op.create_index(
        "ix_deletion_requests_tenant_patient",
        "deletion_requests",
        ["tenant_id", "patient_id"],
    )
    # At most one NON-TERMINAL (pending/approved) request per patient — the DB backstop for the
    # service-level "an open request already exists" guard against a race.
    op.create_index(
        "uq_deletion_requests_open_per_patient",
        "deletion_requests",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'approved')"),
    )

    op.execute("ALTER TABLE deletion_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deletion_requests FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON deletion_requests "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )

    # Tombstone marker: set when a request is executed (the erasure anonymizes the patient row
    # rather than deleting it). Nullable, additive — the patients table keeps its app DML.
    op.add_column(
        "patients",
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patients", "erased_at")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON deletion_requests")
    op.drop_index("uq_deletion_requests_open_per_patient", table_name="deletion_requests")
    op.drop_index("ix_deletion_requests_tenant_patient", table_name="deletion_requests")
    op.drop_table("deletion_requests")
