"""Staff invitations — a single-use credential that onboards a colleague into a role.

Mirrors patient_invitations (0012): RLS ENABLE + FORCE with the tenant predicate;
tenant/user FKs (RESTRICT for the owning tenant, SET NULL for the user provenance links);
only the SHA-256 token hash is stored; the row is operationally mutable (redeem/revoke), and
the immutable record of each transition is the append-only audit trail. Unlike the patient
credential, it carries the ROLE the owner grants — DB-CHECK-enforced against the closed role
vocabulary (mirroring memberships.role, 0009), since the redeemer's privilege depends on it.

Revision ID: 0013_staff_invitations
Revises: 0012_patient_invitations
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_staff_invitations"
down_revision = "0012_patient_invitations"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"
_ROLES = "'owner', 'clinician', 'assistant', 'medical_director'"


def upgrade() -> None:
    op.create_table(
        "staff_invitations",
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
            "role",
            sa.Enum(
                "owner",
                "clinician",
                "assistant",
                "medical_director",
                name="role",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "redeemed_user_id",
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
    # DB-enforce the closed role vocabulary (native_enum=False creates no CHECK on its own;
    # mirrors memberships.role in 0009). The redeemer's granted privilege depends on this value.
    op.create_check_constraint("staff_invitations_role", "staff_invitations", f"role IN ({_ROLES})")
    op.execute("ALTER TABLE staff_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE staff_invitations FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON staff_invitations "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON staff_invitations")
    op.drop_table("staff_invitations")
