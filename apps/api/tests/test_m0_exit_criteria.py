"""Milestone 0 exit criteria:

A clinic user can authenticate, select an authorized tenant, create a synthetic patient,
and all access is audited and tenant-tested.
"""

from __future__ import annotations

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login, provision_staff, select_tenant


def test_authenticate_select_tenant_create_patient_audited(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = provision_staff(
        admin_session,
        email="clinician@synthetic.example",
        tenant_name="Synthetic Clinic",
        tenant_slug="synthetic-clinic",
        role=Role.CLINICIAN,
    )

    # 1) authenticate
    login_resp = login(client, "clinician@synthetic.example")
    assert login_resp.json()["user"]["email"] == "clinician@synthetic.example"
    assert len(login_resp.json()["tenants"]) == 1

    # before tenant selection, there is no active tenant
    me_before = client.get("/api/v1/auth/me").json()
    assert me_before["active_tenant_id"] is None
    assert me_before["role"] is None

    # 2) select an authorized tenant
    select_tenant(client, tenant.id)
    me_after = client.get("/api/v1/auth/me").json()
    assert me_after["active_tenant_id"] == str(tenant.id)
    assert me_after["role"] == "clinician"

    # 3) create a synthetic patient
    create_resp = client.post("/api/v1/patients", json={"display_name": "Synthetic Patient A"})
    assert create_resp.status_code == 201, create_resp.text
    patient = create_resp.json()
    assert patient["is_synthetic"] is True
    patient_id = patient["id"]

    listed = client.get("/api/v1/patients")
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()] == [patient_id]

    # 4) all access is audited
    actions = (
        admin_session.execute(select(AuditEvent.action).order_by(AuditEvent.created_at))
        .scalars()
        .all()
    )
    assert "auth.dev_login" in actions
    assert "tenant.select" in actions
    assert "patient.create" in actions
    assert "patient.list" in actions

    # patient.create is attributable to the user and tenant, and references the patient
    create_event = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "patient.create")
    ).scalar_one()
    assert create_event.actor_user_id == user.id
    assert create_event.tenant_id == tenant.id
    assert str(create_event.target_id) == patient_id
