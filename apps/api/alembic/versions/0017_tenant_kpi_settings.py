"""Per-tenant KPI configuration (owner-managed) — additive, tenant-scoped, RLS-protected.

Owners select which of the GLOBAL, read-only KPI catalog entries (ADR-0004) are active and
visible FOR THEIR OWN CLINIC. This never mutates the shared catalog: the catalog stays closed
and read-only to the app role (0004/0005 REVOKEs); this new table records only a per-tenant
override on top of it. The effective value is COALESCE(tenant override, catalog default).

`tenant_kpi_settings` is a normal tenant-scoped table with the same isolation posture as
patient_invitations / deletion_requests: ENABLE + FORCE row-level security with the standard
tenant predicate, and a unique (tenant_id, kpi_code) so at most one override per KPI per clinic.
It carries NO patient data and NO free text — only IDs, booleans, and timestamps. The app role's
DML on it comes from the ALTER DEFAULT PRIVILEGES grant in 0002 (like 0015); the catalog REVOKEs
are unaffected.

Revision ID: 0017_tenant_kpi_settings
Revises: 0016_erasure_redaction
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_tenant_kpi_settings"
down_revision = "0016_erasure_redaction"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "tenant_kpi_settings",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kpi_code",
            sa.String(length=80),
            sa.ForeignKey("kpi_catalog.code", ondelete="CASCADE"),
            nullable=False,
        ),
        # The per-tenant override of the catalog's global `default_enabled`.
        sa.Column("enabled", sa.Boolean(), nullable=False),
        # NULL override => inherit the catalog's own visibility flag (no per-tenant change).
        sa.Column("patient_visible_override", sa.Boolean(), nullable=True),
        sa.Column("clinician_visible_override", sa.Boolean(), nullable=True),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # At most one override per KPI per clinic. tenant_id leads, so this index also serves
        # the tenant-scoped list query.
        sa.UniqueConstraint("tenant_id", "kpi_code", name="uq_tenant_kpi_settings_tenant_kpi"),
    )

    op.execute("ALTER TABLE tenant_kpi_settings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_kpi_settings FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON tenant_kpi_settings "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenant_kpi_settings")
    op.drop_table("tenant_kpi_settings")
