"""security: app role, grants, row-level security, append-only audit

Creates the non-superuser application role `hadp_app`, grants it DML, and enables
row-level security on every tenant-scoped table so a query can only ever see rows for
the tenant bound to the current transaction (`app.current_tenant`). This is the
defense-in-depth that makes cross-tenant isolation enforceable at the database, not
merely in application code. The audit table is made append-only.

Revision ID: 0002_security_rls
Revises: 4ec0adc6754b
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_security_rls"
down_revision: str | None = "4ec0adc6754b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tenant-scoped tables: every row carries tenant_id and is isolated by RLS.
TENANT_TABLES = [
    "patients",
    "consent_records",
    "source_documents",
    "import_jobs",
    "import_rows",
    "review_items",
    "observations",
    "reports",
    "report_versions",
    "report_evidence",
    "patient_access_links",
]

# Identity/tenancy tables are intentionally NOT tenant-RLS-protected: they are queried
# before a tenant is selected (login, "which tenants may I access"). Access to them is
# governed by application authorization.
NON_RLS_TABLES = ["users", "tenants", "memberships", "auth_sessions"]

# NULLIF(..., '') matters: once `app.current_tenant` has been set locally in a session,
# it reverts to '' (empty string) — not NULL — at transaction end on a pooled connection.
# Casting '' to uuid errors; NULLIF turns it into NULL so the predicate cleanly denies.
_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    # 1) Application role (idempotent; production manages its own credentials).
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hadp_app') THEN
            CREATE ROLE hadp_app LOGIN PASSWORD 'hadp_app'
              NOSUPERUSER NOCREATEDB NOCREATEROLE;
          END IF;
        END $$;
        """
    )

    # 2) Grants: schema usage + DML on existing and future tables.
    op.execute("GRANT USAGE ON SCHEMA public TO hadp_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hadp_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hadp_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hadp_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO hadp_app"
    )

    # 3) RLS on tenant-scoped tables: ENABLE + FORCE so the policy always applies, then a
    #    single ALL policy that scopes both reads (USING) and writes (WITH CHECK).
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )

    # 4) audit_events: tenant-scoped reads; inserts allowed for the current tenant or for
    #    tenant-less security events (e.g. login); never UPDATE/DELETE (append-only).
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    # Tenant-scoped reads, plus tenant-less security events (login/logout). Allowing NULL
    # here is also required so INSERT ... RETURNING of a tenant-less audit row succeeds:
    # RETURNING re-applies the SELECT policy to the new row.
    op.execute(
        "CREATE POLICY audit_select ON audit_events FOR SELECT "
        f"USING (tenant_id IS NULL OR {_TENANT_PREDICATE})"
    )
    op.execute(
        "CREATE POLICY audit_insert ON audit_events FOR INSERT "
        f"WITH CHECK (tenant_id IS NULL OR {_TENANT_PREDICATE})"
    )
    # No UPDATE/DELETE policy => denied by RLS. Also revoke the privilege from the app role.
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM hadp_app")

    # Append-only enforced for everyone via a trigger (row-level UPDATE/DELETE blocked).
    # TRUNCATE is left to privileged admins (hadp_app has no TRUNCATE privilege).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_audit_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_audit_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS hadp_block_audit_mutation()")
    op.execute("DROP POLICY IF EXISTS audit_insert ON audit_events")
    op.execute("DROP POLICY IF EXISTS audit_select ON audit_events")
    op.execute("ALTER TABLE audit_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY")
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    # Grants/role are left in place on downgrade (role may be shared across databases).
