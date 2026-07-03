"""Consent write API + login-failure auditing (Phase 1C slice).

Consent grant/withdraw become product operations: append-only events recorded through
the API by care staff (owner/clinician/assistant — the medical director is the gate,
not an operator), audited with the purpose only. Withdrawal keeps its P0 semantics
(revokes live patient links in the same transaction). Failed logins are audited on an
independent transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.enums import Role
from tests.helpers import login_as, switch_role

_IMPORT = {
    "values": [
        {
            "original_name": "LDL Cholesterol",
            "original_value": "2.8",
            "original_unit": "mmol/L",
            "observed_at": "2025-06-10T00:00:00Z",
            "observed_at_is_date_only": True,
        }
    ]
}


def test_consent_grant_via_api_unlocks_release(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # The assistant records consent (operational care staff), per WORKFLOW §2.4.
    _user, tenant = login_as(
        client,
        admin_session,
        email="capi-assistant@synthetic.example",
        tenant_name="Consent API Clinic",
        tenant_slug="consent-api-clinic",
        role=Role.ASSISTANT,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "CA Patient"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)

    granted = client.post(
        f"/api/v1/patients/{pid}/consents",
        json={"purpose": "report_release", "channel": "in_person"},
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["event_type"] == "granted"
    assert granted.json()["purpose"] == "report_release"

    # Audited with the purpose only.
    event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "consent.granted"))
        .scalars()
        .one()
    )
    assert event.detail == {"purpose": "report_release"}

    # The gate consumes the API-recorded grant: clinician approves, MD releases.
    switch_role(
        client,
        admin_session,
        email="capi-clin@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email="capi-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{rid}/release").status_code == 200


def test_consent_withdraw_via_api_revokes_access(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="cw-clin@synthetic.example",
        tenant_name="Withdraw API Clinic",
        tenant_slug="withdraw-api-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "CW Patient"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    assert (
        client.post(
            f"/api/v1/patients/{pid}/consents",
            json={"purpose": "report_release", "channel": "in_person"},
        ).status_code
        == 201
    )
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email="cw-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    token = client.post(f"/api/v1/reports/{rid}/release").json()["patient_access_token"]
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 200

    # Withdrawal via the API (clinician records it): access stops immediately.
    switch_role(
        client,
        admin_session,
        email="cw-clin2@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    withdrawn = client.post(
        f"/api/v1/patients/{pid}/consents/withdraw",
        json={"purpose": "report_release", "channel": "in_person"},
    )
    assert withdrawn.status_code == 201, withdrawn.text
    assert withdrawn.json()["event_type"] == "withdrawn"
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 404

    # Both events persist append-only; the withdrawal is audited with the purpose only.
    events = admin_session.execute(select(ConsentEvent)).scalars().all()
    assert sorted(e.event_type.value for e in events) == ["granted", "withdrawn"]
    audit = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "consent.withdrawn"))
        .scalars()
        .one()
    )
    assert audit.detail == {"purpose": "report_release"}


def test_medical_director_cannot_record_consent(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="cnr-clin@synthetic.example",
        tenant_name="NoConsent Clinic",
        tenant_slug="noconsent-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "NC Patient"}).json()["id"]
    switch_role(
        client,
        admin_session,
        email="cnr-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    resp = client.post(
        f"/api/v1/patients/{pid}/consents",
        json={"purpose": "report_release", "channel": "in_person"},
    )
    assert resp.status_code == 403


def test_consent_negatives(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Unauthenticated.
    assert (
        client.post(
            f"/api/v1/patients/{uuid.uuid4()}/consents",
            json={"purpose": "report_release", "channel": "x"},
        ).status_code
        == 401
    )
    login_as(
        client,
        admin_session,
        email="cn-a@synthetic.example",
        tenant_name="CN A",
        tenant_slug="cn-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "CN Patient"}).json()["id"]
    # Closed purpose vocabulary: an invented value is rejected at the boundary.
    assert (
        client.post(
            f"/api/v1/patients/{pid}/consents",
            json={"purpose": "marketing", "channel": "in_person"},
        ).status_code
        == 422
    )
    # Cross-tenant patient is a 404 (no info leak).
    login_as(
        client,
        admin_session,
        email="cn-b@synthetic.example",
        tenant_name="CN B",
        tenant_slug="cn-b",
        role=Role.CLINICIAN,
    )
    assert (
        client.post(
            f"/api/v1/patients/{pid}/consents",
            json={"purpose": "report_release", "channel": "in_person"},
        ).status_code
        == 404
    )


def test_failed_login_is_audited(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/auth/dev-login", json={"email": "nobody@synthetic.example"})
    assert resp.status_code == 401
    event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "login.failed"))
        .scalars()
        .one()
    )
    # Reason code only — the attempted identifier is never recorded.
    assert event.detail == {"reason": "unknown_user"}
    assert event.actor_user_id is None
