"""Server-side, deny-by-default authorization."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.auth.authz import Action, can
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login, login_as, provision_staff, select_tenant


def test_unauthenticated_cannot_create_patient(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": "X"})
    assert resp.status_code == 401


def test_unauthenticated_cannot_list_patients(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/patients")
    assert resp.status_code == 401


def test_authenticated_without_tenant_is_denied(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    provision_staff(
        admin_session,
        email="notenant@synthetic.example",
        tenant_name="Clinic NT",
        tenant_slug="clinic-nt",
        role=Role.CLINICIAN,
    )
    login(client, "notenant@synthetic.example")
    # No tenant selected -> deny-by-default
    resp = client.post("/api/v1/patients", json={"display_name": "X"})
    assert resp.status_code == 403


def test_cannot_select_tenant_without_membership(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    provision_staff(
        admin_session,
        email="member@synthetic.example",
        tenant_name="Clinic M",
        tenant_slug="clinic-m",
        role=Role.CLINICIAN,
    )
    login(client, "member@synthetic.example")
    # A tenant the user is not a member of
    resp = client.post("/api/v1/tenancy/select-tenant", json={"tenant_id": str(uuid.uuid4())})
    assert resp.status_code == 403


def test_validation_error_does_not_echo_input(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = provision_staff(
        admin_session,
        email="val@synthetic.example",
        tenant_name="Clinic V",
        tenant_slug="clinic-v",
        role=Role.CLINICIAN,
    )
    login(client, "val@synthetic.example")
    select_tenant(client, tenant.id)
    # Missing required display_name
    resp = client.post("/api/v1/patients", json={"external_ref": "SECRET-REF-12345"})
    assert resp.status_code == 422
    assert "SECRET-REF-12345" not in resp.text
    assert resp.json()["error"]["code"] == "validation_failed"


def test_clinician_only_can_approve_and_release() -> None:
    # The clinician-in-the-loop doctrine encoded in the authz matrix.
    assert can(Role.CLINICIAN, Action.REPORT_APPROVE) is True
    assert can(Role.CLINICIAN, Action.REPORT_RELEASE) is True
    assert can(Role.ASSISTANT, Action.REPORT_APPROVE) is False
    assert can(Role.OWNER, Action.REPORT_APPROVE) is False
    assert can(Role.ASSISTANT, Action.REPORT_RELEASE) is False
    assert can(Role.OWNER, Action.REPORT_RELEASE) is False


def test_assistant_cannot_approve_via_api(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="assistant@synthetic.example",
        tenant_name="Clinic AS",
        tenant_slug="clinic-as",
        role=Role.ASSISTANT,
    )
    # Role is checked in the dependency before the report is even looked up.
    resp = client.post(f"/api/v1/reports/{uuid.uuid4()}/approve")
    assert resp.status_code == 403


def test_failed_authorization_is_audited(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    provision_staff(
        admin_session,
        email="denied@synthetic.example",
        tenant_name="Clinic D",
        tenant_slug="clinic-d",
        role=Role.CLINICIAN,
    )
    login(client, "denied@synthetic.example")  # authenticated but no tenant selected
    assert client.post("/api/v1/patients", json={"display_name": "X"}).status_code == 403

    # The denial is recorded on its own committed transaction (survives request rollback).
    actions = (
        admin_session.execute(select(AuditEvent.action).order_by(AuditEvent.created_at))
        .scalars()
        .all()
    )
    assert "authz.denied" in actions
