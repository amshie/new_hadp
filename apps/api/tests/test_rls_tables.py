"""Every table that holds a clinic's rows is under row-level security — enabled AND forced.

ENABLE alone does not bind the table's owner; FORCE does. The application role is not the
owner, but the guarantee must not depend on which role a deployment happens to connect as
(a managed database's admin user may be neither superuser nor BYPASSRLS, and then owns every
table). No test asserted this; a new tenant table without FORCE would have gone unnoticed.
"""

from __future__ import annotations

from sqlalchemy import text

# A `tenant_id` column without row-level security, each for a stated reason.
_NOT_UNDER_RLS = {
    # Read before a clinic is selected (which clinics may this user enter?), by user id.
    "memberships",
}


def test_every_table_with_a_tenant_column_enables_and_forces_rls(admin_session) -> None:  # type: ignore[no-untyped-def]
    rows = admin_session.execute(
        text(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                   (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
              JOIN pg_attribute a ON a.attrelid = c.oid
             WHERE n.nspname = 'public' AND c.relkind = 'r'
               AND a.attname = 'tenant_id' AND NOT a.attisdropped
             ORDER BY c.relname
            """
        )
    ).all()
    tables = {name for name, *_ in rows}
    assert len(tables) >= 15, f"the scan found too few tenant tables to mean anything: {tables}"
    assert tables >= _NOT_UNDER_RLS, "a table named as an exception no longer exists"

    unprotected = sorted(
        name
        for name, enabled, forced, policies in rows
        if name not in _NOT_UNDER_RLS and not (enabled and forced and policies >= 1)
    )
    assert not unprotected, f"tenant tables without ENABLE + FORCE + a policy: {unprotected}"
