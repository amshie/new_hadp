"""REJECTED is reachable and attributable (Gate G2 slice).

A clinician may withdraw a draft or their approval; a medical director may refuse at the
release gate. A released version can never be re-labeled rejected. Rejection is a
preserved record: editing afterwards creates a NEW version; approval of a rejected
version is impossible.
"""

from __future__ import annotations

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.reports.models import ReportVersion
from tests.helpers import grant_release_consent, login_as, switch_role

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


def _draft_report(client, slug: str) -> str:  # type: ignore[no-untyped-def]
    pid = client.post("/api/v1/patients", json={"display_name": f"R {slug}"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    return client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]


def test_clinician_rejects_a_draft_attributably(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = login_as(
        client,
        admin_session,
        email="rej@synthetic.example",
        tenant_name="Reject Clinic",
        tenant_slug="reject-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "a")
    resp = client.post(f"/api/v1/reports/{rid}/reject")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    version = admin_session.execute(select(ReportVersion)).scalars().one()
    assert version.rejected_by_user_id == user.id
    assert version.rejected_at is not None
    actions = admin_session.execute(select(AuditEvent.action)).scalars().all()
    assert "report.rejected" in actions

    # A rejected version cannot be approved (it is not a draft state).
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 409
    # Rejecting again is a conflict, not a silent no-op.
    assert client.post(f"/api/v1/reports/{rid}/reject").status_code == 409


def test_medical_director_refuses_an_approved_report(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rej-clin@synthetic.example",
        tenant_name="Refuse Clinic",
        tenant_slug="refuse-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "b")
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200

    switch_role(
        client,
        admin_session,
        email="rej-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    resp = client.post(f"/api/v1/reports/{rid}/reject")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"
    # No release after refusal.
    assert client.post(f"/api/v1/reports/{rid}/release").status_code == 409


def test_assistant_cannot_reject(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rej-clin2@synthetic.example",
        tenant_name="NoReject Clinic",
        tenant_slug="noreject-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "c")
    switch_role(
        client,
        admin_session,
        email="rej-assistant@synthetic.example",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    assert client.post(f"/api/v1/reports/{rid}/reject").status_code == 403


def test_released_report_cannot_be_rejected(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rej-rel@synthetic.example",
        tenant_name="Released Clinic",
        tenant_slug="released-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "d")
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    report_patient = client.get(f"/api/v1/reports/{rid}").json()["patient_id"]
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=report_patient)
    switch_role(
        client,
        admin_session,
        email="rej-rel-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{rid}/release").status_code == 200
    assert client.post(f"/api/v1/reports/{rid}/reject").status_code == 409


def test_edit_after_reject_creates_a_new_version(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rej-edit@synthetic.example",
        tenant_name="Rework Clinic",
        tenant_slug="rework-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "e")
    report = client.get(f"/api/v1/reports/{rid}").json()
    assert client.post(f"/api/v1/reports/{rid}/reject").status_code == 200

    statements = [
        {
            "id": s["id"],
            "text": s["text"] + " (überarbeitet)",
            "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
        }
        for s in report["statements"]
    ]
    edited = client.post(f"/api/v1/reports/{rid}/edit", json={"statements": statements})
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "draft_edited"
    assert edited.json()["version_no"] == report["version_no"] + 1

    # The rejected version is preserved (append-only record), not mutated back to draft.
    versions = admin_session.execute(select(ReportVersion)).scalars().all()
    statuses = sorted(v.status.value for v in versions)
    assert statuses == ["draft_edited", "rejected"]

    # The rework can pass the gate again: clinician approves, medical director releases.
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    report_patient = client.get(f"/api/v1/reports/{rid}").json()["patient_id"]
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=report_patient)
    switch_role(
        client,
        admin_session,
        email="rej-edit-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{rid}/release").status_code == 200
