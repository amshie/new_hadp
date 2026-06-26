"""Consent events are append-only; report release is consent-gated; withdrawal is a new event.

P0: consent is an append-only stream (ConsentEvent). Patient-facing report release is fail-closed on
an ACTIVE report_release consent; withdrawing consent is a NEW event (never an in-place edit) and
revokes any live patient access link in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, InternalError, ProgrammingError

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.enums import ConsentEventType, ConsentPurpose, Role
from hadp_api.modules.patients.models import Patient
from tests.helpers import grant_release_consent, login_as, make_tenant


def _grant(
    admin_session,  # type: ignore[no-untyped-def]
    *,
    tenant_id,
    patient_id,
    purpose=ConsentPurpose.REPORT_RELEASE,
    event_type=ConsentEventType.GRANTED,
    recorded_at=None,
):
    event = ConsentEvent(
        tenant_id=tenant_id,
        patient_id=patient_id,
        purpose=purpose,
        event_type=event_type,
        consent_text_version="synthetic-v1",
        channel="in_person",
        recorded_at=recorded_at or datetime.now(UTC),
    )
    admin_session.add(event)
    return event


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


def test_consent_events_are_append_only(admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = make_tenant(admin_session, name="Consent AO", slug="consent-ao")
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    event = ConsentEvent(
        tenant_id=tenant.id,
        patient_id=patient.id,
        purpose=ConsentPurpose.REPORT_RELEASE,
        event_type=ConsentEventType.GRANTED,
        consent_text_version="synthetic-v1",
        channel="in_person",
        recorded_at=datetime.now(UTC),
    )
    admin_session.add(event)
    admin_session.commit()

    # UPDATE and DELETE are blocked by the append-only trigger, even for the admin/owner.
    with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
        admin_session.execute(
            text("UPDATE consent_events SET channel = 'x' WHERE id = :i"), {"i": event.id}
        )
    admin_session.rollback()
    with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
        admin_session.execute(text("DELETE FROM consent_events WHERE id = :i"), {"i": event.id})
    admin_session.rollback()

    still = admin_session.get(ConsentEvent, event.id)
    assert still is not None
    assert still.event_type == ConsentEventType.GRANTED
    assert still.channel == "in_person"


def test_release_is_consent_gated(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="consentgate@synthetic.example",
        tenant_name="Consent Gate Clinic",
        tenant_slug="consent-gate-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "CG Patient"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    client.post(f"/api/v1/reports/{rid}/approve")

    # Fail-closed: an approved report cannot be released without an active report_release consent.
    blocked = client.post(f"/api/v1/reports/{rid}/release")
    assert blocked.status_code == 409, blocked.text

    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    ok = client.post(f"/api/v1/reports/{rid}/release")
    assert ok.status_code == 200, ok.text


def test_withdrawal_is_a_new_event_and_revokes_access(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = login_as(
        client,
        admin_session,
        email="withdraw@synthetic.example",
        tenant_name="Withdraw Clinic",
        tenant_slug="withdraw-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "WD Patient"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    client.post(f"/api/v1/reports/{rid}/approve")
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    token = client.post(f"/api/v1/reports/{rid}/release").json()["patient_access_token"]
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 200

    # Withdraw consent via the service (no HTTP route in P0); on its own tenant-bound session.
    session = get_sessionmaker()()
    set_tenant_context(session, tenant.id, user.id)
    try:
        consents_service.withdraw_consent(
            session,
            tenant_id=tenant.id,
            patient_id=uuid.UUID(pid),
            purpose=ConsentPurpose.REPORT_RELEASE,
            channel="in_person",
            recorded_by_user_id=user.id,
        )
        session.commit()
    finally:
        session.close()

    # The live patient link is revoked the moment consent is withdrawn.
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 404

    # Withdrawal is a NEW event: both rows exist, the GRANTED row is unchanged, state is inactive.
    check = get_sessionmaker()()
    set_tenant_context(check, tenant.id, user.id)
    try:
        events = (
            check.execute(
                select(ConsentEvent).where(
                    ConsentEvent.patient_id == uuid.UUID(pid),
                    ConsentEvent.purpose == ConsentPurpose.REPORT_RELEASE,
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 2
        assert {e.event_type for e in events} == {
            ConsentEventType.GRANTED,
            ConsentEventType.WITHDRAWN,
        }
        assert (
            consents_service.has_active_consent(
                check,
                tenant_id=tenant.id,
                patient_id=uuid.UUID(pid),
                purpose=ConsentPurpose.REPORT_RELEASE,
            )
            is False
        )
    finally:
        check.close()


def test_consent_events_revoke_and_rls_under_app_role(admin_session) -> None:  # type: ignore[no-untyped-def]
    """Under the real runtime role (hadp_app): UPDATE/DELETE are denied by REVOKE (not merely the
    trigger), and RLS is fail-closed — no rows are visible without a bound tenant context."""
    tenant = make_tenant(admin_session, name="Consent App", slug="consent-app")
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    event = _grant(admin_session, tenant_id=tenant.id, patient_id=patient.id)
    admin_session.commit()

    # RLS fail-closed: with no app.current_tenant the hadp_app role sees zero rows.
    blind = get_sessionmaker()()
    try:
        assert blind.execute(text("SELECT count(*) FROM consent_events")).scalar() == 0
    finally:
        blind.close()

    # With the bound tenant context the row IS visible to hadp_app.
    scoped = get_sessionmaker()()
    set_tenant_context(scoped, tenant.id)
    try:
        assert scoped.execute(text("SELECT count(*) FROM consent_events")).scalar() == 1
    finally:
        scoped.close()

    # REVOKE bites: UPDATE and DELETE are permission-denied to hadp_app (each on its own txn).
    for stmt in (
        "UPDATE consent_events SET channel = 'x' WHERE id = :i",
        "DELETE FROM consent_events WHERE id = :i",
    ):
        sess = get_sessionmaker()()
        set_tenant_context(sess, tenant.id)
        try:
            with pytest.raises((DBAPIError, ProgrammingError)) as excinfo:
                sess.execute(text(stmt), {"i": event.id})
            assert "permission denied" in str(excinfo.value).lower()
        finally:
            sess.rollback()
            sess.close()


def test_consent_is_tenant_scoped(admin_session) -> None:  # type: ignore[no-untyped-def]
    """A grant under tenant A must not satisfy a release queried under tenant B (and vice versa)."""
    tenant_a = make_tenant(admin_session, name="A", slug="consent-ta")
    tenant_b = make_tenant(admin_session, name="B", slug="consent-tb")
    patient = Patient(tenant_id=tenant_a.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    _grant(admin_session, tenant_id=tenant_a.id, patient_id=patient.id)
    admin_session.commit()

    assert (
        consents_service.has_active_consent(
            admin_session,
            tenant_id=tenant_a.id,
            patient_id=patient.id,
            purpose=ConsentPurpose.REPORT_RELEASE,
        )
        is True
    )
    assert (
        consents_service.has_active_consent(
            admin_session,
            tenant_id=tenant_b.id,
            patient_id=patient.id,
            purpose=ConsentPurpose.REPORT_RELEASE,
        )
        is False
    )


def test_wrong_purpose_consent_does_not_unlock_release(admin_session) -> None:  # type: ignore[no-untyped-def]
    """An ANALYTICS grant must not unlock report_release — purposes are independent."""
    tenant = make_tenant(admin_session, name="Purpose", slug="consent-purpose")
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    _grant(
        admin_session, tenant_id=tenant.id, patient_id=patient.id, purpose=ConsentPurpose.ANALYTICS
    )
    admin_session.commit()

    assert (
        consents_service.has_active_consent(
            admin_session,
            tenant_id=tenant.id,
            patient_id=patient.id,
            purpose=ConsentPurpose.ANALYTICS,
        )
        is True
    )
    assert (
        consents_service.has_active_consent(
            admin_session,
            tenant_id=tenant.id,
            patient_id=patient.id,
            purpose=ConsentPurpose.REPORT_RELEASE,
        )
        is False
    )


def test_regrant_after_withdraw_restores_consent(admin_session) -> None:  # type: ignore[no-untyped-def]
    """Latest-event-wins: grant -> withdraw -> grant leaves consent active again."""
    tenant = make_tenant(admin_session, name="Regrant", slug="consent-regrant")
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    t0 = datetime.now(UTC)
    _grant(admin_session, tenant_id=tenant.id, patient_id=patient.id, recorded_at=t0)
    _grant(
        admin_session,
        tenant_id=tenant.id,
        patient_id=patient.id,
        event_type=ConsentEventType.WITHDRAWN,
        recorded_at=t0 + timedelta(seconds=1),
    )
    _grant(
        admin_session,
        tenant_id=tenant.id,
        patient_id=patient.id,
        recorded_at=t0 + timedelta(seconds=2),
    )
    admin_session.commit()

    assert (
        consents_service.has_active_consent(
            admin_session,
            tenant_id=tenant.id,
            patient_id=patient.id,
            purpose=ConsentPurpose.REPORT_RELEASE,
        )
        is True
    )
