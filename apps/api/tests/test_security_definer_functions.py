"""A function that runs with its owner's rights resolves its names itself.

`SECURITY DEFINER` functions run as their owner — here the migrating superuser. One that
names tables without a schema and has no search_path of its own lets the CALLER decide what
those names mean: a temporary table of the caller's is found before the real one. For the
application role that was the one path to its owner's rights (migration 0020).
"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from tests.helpers import make_tenant

# Every function in the schema that runs with its owner's rights. A new one belongs here —
# after its search_path has been looked at.
_DEFINER_FUNCTIONS = {"hadp_execute_patient_erasure"}


def test_every_security_definer_function_pins_its_search_path(admin_session) -> None:  # type: ignore[no-untyped-def]
    rows = admin_session.execute(
        text(
            """
            SELECT p.proname, p.proconfig
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'public' AND p.prosecdef
            """
        )
    ).all()
    assert {name for name, _config in rows} == _DEFINER_FUNCTIONS

    for name, config in rows:
        pinned = [setting for setting in (config or []) if setting.startswith("search_path=")]
        assert pinned, f"{name} resolves its names on the caller's search_path"
        path = [schema.strip().strip('"') for schema in pinned[0].split("=", 1)[1].split(",")]
        # Catalog first, and a temporary schema named — so that it is searched last, not first.
        assert path[0] == "pg_catalog", (name, path)
        assert path[-1] == "pg_temp" and "pg_temp" not in path[:-1], (name, path)


def test_a_callers_temporary_table_does_not_stand_in_for_a_real_one(admin_session) -> None:  # type: ignore[no-untyped-def]
    """As the application role: a temporary table named like one the erasure function
    rewrites is left alone — the function works on the real table."""
    tenant = make_tenant(admin_session, name="Clinic definer", slug="definer")
    admin_session.commit()
    patient_id = uuid.uuid4()

    with get_sessionmaker()() as session:
        set_tenant_context(session, tenant.id)
        session.execute(
            text(
                "CREATE TEMP TABLE interpretation_runs"
                " (id uuid, tenant_id uuid, patient_id uuid, reason text) ON COMMIT DROP"
            )
        )
        session.execute(
            text(
                "INSERT INTO pg_temp.interpretation_runs (id, tenant_id, patient_id, reason)"
                " VALUES (:id, :tenant, :patient, 'placed by the caller')"
            ),
            {"id": uuid.uuid4(), "tenant": tenant.id, "patient": patient_id},
        )

        session.execute(
            text("SELECT hadp_execute_patient_erasure(:tenant, :patient)"),
            {"tenant": tenant.id, "patient": patient_id},
        )

        untouched = session.execute(
            text("SELECT reason FROM pg_temp.interpretation_runs")
        ).scalar_one()
        session.rollback()
    assert untouched == "placed by the caller"
