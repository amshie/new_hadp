"""Cross-tenant isolation — enforced in application code AND by PostgreSQL RLS."""

from __future__ import annotations

from sqlalchemy import func, select

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.enums import Role
from hadp_api.modules.patients.models import Patient
from tests.helpers import (
    grant_release_consent,
    login,
    login_as,
    provision_staff,
    select_tenant,
)


def test_api_tenant_cannot_see_other_tenant_patients(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Clinic A clinician creates a patient.
    _, tenant_a = login_as(
        client,
        admin_session,
        email="a@synthetic.example",
        tenant_name="Clinic A",
        tenant_slug="clinic-a",
        role=Role.CLINICIAN,
    )
    created = client.post("/api/v1/patients", json={"display_name": "Patient A1"})
    assert created.status_code == 201

    # Clinic B clinician (separate session) sees none of Clinic A's patients.
    provision_staff(
        admin_session,
        email="b@synthetic.example",
        tenant_name="Clinic B",
        tenant_slug="clinic-b",
        role=Role.CLINICIAN,
    )
    # New client => fresh cookie jar (separate principal/session).
    from fastapi.testclient import TestClient

    from hadp_api.main import app

    with TestClient(app) as client_b:
        login(client_b, "b@synthetic.example")
        # Find tenant B id from my-tenants
        tenants = client_b.get("/api/v1/tenancy/my-tenants").json()
        tenant_b_id = tenants[0]["tenant_id"]
        select_tenant(client_b, tenant_b_id)
        listed = client_b.get("/api/v1/patients")
        assert listed.status_code == 200
        assert listed.json() == []


def test_rls_blocks_direct_cross_tenant_reads(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Seed two tenants with one patient each (admin bypasses RLS for setup).
    from hadp_api.modules.tenancy.models import Tenant

    t_a = Tenant(name="RLS A", slug="rls-a", is_synthetic=True)
    t_b = Tenant(name="RLS B", slug="rls-b", is_synthetic=True)
    admin_session.add_all([t_a, t_b])
    admin_session.flush()
    admin_session.add_all(
        [
            Patient(tenant_id=t_a.id, display_name="A", is_synthetic=True),
            Patient(tenant_id=t_b.id, display_name="B", is_synthetic=True),
        ]
    )
    admin_session.commit()

    sessionmaker = get_sessionmaker()

    # Scoped to tenant A -> sees exactly one patient (A's).
    with sessionmaker() as s:
        set_tenant_context(s, t_a.id)
        count_a = s.execute(select(func.count()).select_from(Patient)).scalar_one()
        ids = s.execute(select(Patient.tenant_id)).scalars().all()
        s.rollback()
    assert count_a == 1
    assert ids == [t_a.id]

    # With NO tenant context, RLS denies all rows (deny-by-default).
    with sessionmaker() as s:
        count_none = s.execute(select(func.count()).select_from(Patient)).scalar_one()
        s.rollback()
    assert count_none == 0


def test_cross_tenant_access_by_resource_id_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Clinic A creates a patient.
    _, _tenant_a = login_as(
        client,
        admin_session,
        email="ida@synthetic.example",
        tenant_name="Clinic IDA",
        tenant_slug="clinic-ida",
        role=Role.CLINICIAN,
    )
    pid_a = client.post("/api/v1/patients", json={"display_name": "A patient"}).json()["id"]

    # Clinic B, authenticated, requests Clinic A's patient by id -> 404 (not 200/500).
    from fastapi.testclient import TestClient

    from hadp_api.main import app

    provision_staff(
        admin_session,
        email="idb@synthetic.example",
        tenant_name="Clinic IDB",
        tenant_slug="clinic-idb",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "idb@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        assert cb.get(f"/api/v1/patients/{pid_a}/observations").status_code == 404
        assert (
            cb.post(
                f"/api/v1/patients/{pid_a}/imports",
                json={
                    "values": [
                        {
                            "original_name": "LDL Cholesterol",
                            "original_value": "2.0",
                            "original_unit": "mmol/L",
                            "observed_at": "2025-06-10T00:00:00Z",
                        }
                    ]
                },
            ).status_code
            == 404
        )


def test_cross_tenant_token_replay_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Clinic A produces and releases a report, obtaining a valid patient token.
    _, tenant_a = login_as(
        client,
        admin_session,
        email="tka@synthetic.example",
        tenant_name="Clinic TKA",
        tenant_slug="clinic-tka",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "TK patient"}).json()["id"]
    client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "values": [
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "2.8",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-06-10T00:00:00Z",
                    "observed_at_is_date_only": True,
                }
            ]
        },
    )
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    client.post(f"/api/v1/reports/{rid}/approve")
    grant_release_consent(admin_session, tenant_id=tenant_a.id, patient_id=pid)
    token = client.post(f"/api/v1/reports/{rid}/release").json()["patient_access_token"]

    # Clinic B exists; presenting A's valid token under B's tenant reveals nothing.
    from tests.helpers import make_tenant

    tenant_b = make_tenant(admin_session, name="Clinic TKB", slug="clinic-tkb")
    admin_session.commit()

    correct = client.get(f"/api/v1/patient-view?tenant={tenant_a.id}&token={token}")
    assert correct.status_code == 200  # sanity: correct tenant + token works
    replay = client.get(f"/api/v1/patient-view?tenant={tenant_b.id}&token={token}")
    assert replay.status_code == 404
