"""REJECTED is reachable and attributable (Gate G2 slice), and says why (A8).

A clinician may withdraw a draft or their approval; a medical director may refuse at the
release gate. A released version can never be re-labeled rejected. Rejection is a
preserved record: editing afterwards creates a NEW version; approval of a rejected
version is impossible. Every rejection names a reason from a closed vocabulary — stored on
the version, audited as a code, shown to whoever reworks the report — and never free text.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import ReportRejectionReason, Role
from hadp_api.modules.reports.models import ReportVersion
from tests.helpers import grant_release_consent, login, login_as, select_tenant, switch_role

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


def _reject(client, report_id: str, reason: str = "wording"):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/reports/{report_id}/reject", json={"reason": reason})


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
    resp = _reject(client, rid)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    assert resp.json()["rejection_reason"] == "wording"

    version = admin_session.execute(select(ReportVersion)).scalars().one()
    assert version.rejected_by_user_id == user.id
    assert version.rejected_at is not None
    assert version.rejection_reason == ReportRejectionReason.WORDING
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "report.rejected")
    ).scalar_one()
    # The reason travels as its code — nothing else about the report does.
    assert audit.detail == {"version_no": 1, "reason": "wording"}

    # A rejected version cannot be approved (it is not a draft state).
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 409
    # Rejecting again is a conflict, not a silent no-op.
    assert _reject(client, rid).status_code == 409


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
    resp = _reject(client, rid)
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
    assert _reject(client, rid).status_code == 403


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
    assert _reject(client, rid).status_code == 409


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
    assert _reject(client, rid).status_code == 200

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


def test_a_rejection_must_name_a_reason_from_the_closed_vocabulary(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rej-reason@synthetic.example",
        tenant_name="Reason Clinic",
        tenant_slug="reason-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "f")
    url = f"/api/v1/reports/{rid}/reject"
    # No reason, an empty one, an invented one, free text: all refused at the boundary.
    assert client.post(url).status_code == 422
    assert client.post(url, json={}).status_code == 422
    for invented in ("", "because", "Wording", "LDL was 2.8 for Erika Mustermann"):
        assert client.post(url, json={"reason": invented}).status_code == 422, invented
    # Nothing was rejected, and the refused free text was not written anywhere.
    assert client.get(f"/api/v1/reports/{rid}").json()["status"] == "draft_generated"
    assert (
        admin_session.execute(
            select(AuditEvent).where(AuditEvent.action == "report.rejected")
        ).first()
        is None
    )


@pytest.mark.parametrize("reason", [r.value for r in ReportRejectionReason])
def test_every_reason_of_the_vocabulary_is_accepted_and_shown(
    client, admin_session, reason: str
) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rej-each@synthetic.example",
        tenant_name="Each Reason Clinic",
        tenant_slug="each-reason-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "g")
    resp = _reject(client, rid, reason)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/api/v1/reports/{rid}").json()["rejection_reason"] == reason


def test_the_rework_carries_the_reason_it_answers(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rej-rework@synthetic.example",
        tenant_name="Rework Reason Clinic",
        tenant_slug="rework-reason-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "h")
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    # The medical director sends it back at the release gate, saying why.
    switch_role(
        client,
        admin_session,
        email="rej-rework-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert _reject(client, rid, "evidence_insufficient").status_code == 200

    # The clinician who reworks it reads the reason on the rejected version …
    login(client, "rej-rework@synthetic.example")
    select_tenant(client, tenant.id)
    rejected = client.get(f"/api/v1/reports/{rid}").json()
    assert (rejected["rejection_reason"], rejected["reworks_rejection_reason"]) == (
        "evidence_insufficient",
        None,
    )
    statements = [
        {
            "id": s["id"],
            "text": s["text"] + " (revised)",
            "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
        }
        for s in rejected["statements"]
    ]
    reworked = client.post(f"/api/v1/reports/{rid}/edit", json={"statements": statements})
    assert reworked.status_code == 200, reworked.text
    # … and the new version says which objection it answers, without being rejected itself.
    body = reworked.json()
    assert (body["status"], body["version_no"]) == ("draft_edited", 2)
    assert (body["rejection_reason"], body["reworks_rejection_reason"]) == (
        None,
        "evidence_insufficient",
    )
    # Once approved it is still the answer to that objection; a later version would not be.
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    assert client.get(f"/api/v1/reports/{rid}").json()["reworks_rejection_reason"] == (
        "evidence_insufficient"
    )


def test_the_database_itself_keeps_the_reason_closed_and_on_rejected_versions(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rej-db@synthetic.example",
        tenant_name="DB Reason Clinic",
        tenant_slug="db-reason-clinic",
        role=Role.CLINICIAN,
    )
    rid = _draft_report(client, "i")
    update = text("UPDATE report_versions SET rejection_reason = :reason WHERE report_id = :rid")
    # A reason on a version that is not rejected.
    with pytest.raises(IntegrityError):
        admin_session.execute(update, {"reason": "wording", "rid": rid})
    admin_session.rollback()

    assert _reject(client, rid).status_code == 200
    # A value outside the vocabulary, even on a rejected version.
    with pytest.raises(IntegrityError):
        admin_session.execute(update, {"reason": "free text about a patient", "rid": rid})
    admin_session.rollback()

    # A version rejected before reasons were recorded has none — and none is invented.
    admin_session.execute(update, {"reason": None, "rid": rid})
    admin_session.commit()
    assert client.get(f"/api/v1/reports/{rid}").json()["rejection_reason"] is None
