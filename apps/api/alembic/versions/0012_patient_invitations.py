"""Patient invitations (P1, docs/notes/0010 §4) — synthetic identities only.

A single-use, TTL'd, revocable credential that lets a (synthetic) patient redeem the
report_release consent grant the P0 gate already consumes. Mirrors the platform
posture: RLS ENABLE + FORCE with the tenant predicate; tenant/patient FKs ON DELETE
RESTRICT (erasure is a designed process, never a cascade); only the SHA-256 token
hash is stored. The row is operationally mutable (redeem/revoke lifecycle); the
immutable record of each transition is the append-only audit trail.

Revision ID: 0012_patient_invitations
Revises: 0011_review_item_resolved_at
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_patient_invitations"
down_revision = "0011_review_item_resolved_at"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "patient_invitations",
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
            index=True,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "redeemed",
                "revoked",
                "expired",
                name="invitationstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute("ALTER TABLE patient_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE patient_invitations FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON patient_invitations "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON patient_invitations")
    op.drop_table("patient_invitations")
