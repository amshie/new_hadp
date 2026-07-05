"""Patient onboarding slice (docs/notes/0011): duplicate probe + consent-at-create.

The duplicate probe is conservative (exact normalized matches only), tenant-scoped, and
never leaks across tenants. Creation refuses STRONG duplicates (external_ref, or
name+date of birth) with 409 `duplicate_patient` unless explicitly overridden; weak
name-only matches surface but never block. Onboarding consents append to the existing
ConsentEvent stream in the same transaction as the create, each grant audited with the
purpose only.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.patients.models import Patient
from tests.helpers import login_as, switch_role

_DOB = "1968-04-12"


def _create(client, name: str, **extra):  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": name, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _probe(client, name: str, **extra):  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients/duplicate-check", json={"display_name": name, **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_duplicate_check_matches_and_ranks(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="onb-a@synthetic.example",
        tenant_name="Onboarding Clinic A",
        tenant_slug="onboarding-clinic-a",
        role=Role.ASSISTANT,
    )
    created = _create(client, "Maria Beispiel", date_of_birth=_DOB, external_ref="SYN-DUP-1")

    # Same normalized name + same DOB: strong (case/whitespace-insensitive).
    strong = _probe(client, "  maria   BEISPIEL ", date_of_birth=_DOB)
    assert strong["has_strong_match"] is True
    assert [c["match_basis"] for c in strong["candidates"]] == ["name_dob"]
    assert strong["candidates"][0]["id"] == created["id"]

    # Same name, probe has no DOB: weak — surfaced but not blocking.
    weak = _probe(client, "Maria Beispiel")
    assert weak["has_strong_match"] is False
    assert [c["match_basis"] for c in weak["candidates"]] == ["name"]

    # Same external_ref under a different name: strong, ranked first.
    ref = _probe(client, "Ganz Anderer Name", external_ref="SYN-DUP-1")
    assert ref["has_strong_match"] is True
    assert [c["match_basis"] for c in ref["candidates"]] == ["external_ref"]

    # No overlap at all: empty.
    none = _probe(client, "Niemand Bekanntes")
    assert none == {"candidates": [], "has_strong_match": False}

    # Audited with the candidate COUNT only (never identity details).
    events = (
        admin_session.execute(
            select(AuditEvent).where(AuditEvent.action == "patient.duplicate_check")
        )
        .scalars()
        .all()
    )
    assert len(events) == 4
    assert {frozenset(e.detail.items()) for e in events} == {
        frozenset({("candidates", 1)}),
        frozenset({("candidates", 0)}),
    }


def test_duplicate_check_never_crosses_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Tenant A holds the original.
    login_as(
        client,
        admin_session,
        email="onb-iso-a@synthetic.example",
        tenant_name="Isolation Clinic A",
        tenant_slug="isolation-clinic-a",
        role=Role.CLINICIAN,
    )
    _create(client, "Anna Zweifach", date_of_birth=_DOB, external_ref="SYN-ISO-9")

    # Tenant B probes the very same identity: nothing may surface (explicit scope + RLS).
    login_as(
        client,
        admin_session,
        email="onb-iso-b@synthetic.example",
        tenant_name="Isolation Clinic B",
        tenant_slug="isolation-clinic-b",
        role=Role.CLINICIAN,
    )
    probe = _probe(client, "Anna Zweifach", date_of_birth=_DOB, external_ref="SYN-ISO-9")
    assert probe == {"candidates": [], "has_strong_match": False}

    # And tenant B may create that identity without any duplicate 409 — the guard is
    # tenant-local by construction.
    _create(client, "Anna Zweifach", date_of_birth=_DOB, external_ref="SYN-ISO-9")


def test_create_blocks_strong_duplicates_unless_overridden(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="onb-block@synthetic.example",
        tenant_name="Duplicate Guard Clinic",
        tenant_slug="duplicate-guard-clinic",
        role=Role.ASSISTANT,
    )
    _create(client, "Peter Doppelt", date_of_birth=_DOB)

    # Strong (name+DOB) without the override: 409, nothing persisted.
    blocked = client.post(
        "/api/v1/patients",
        json={"display_name": "peter  doppelt", "date_of_birth": _DOB},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "duplicate_patient"
    count = admin_session.execute(select(Patient).where(Patient.tenant_id == tenant.id)).scalars()
    assert len(list(count)) == 1

    # Weak (name only, no DOB on either side of the pair): never blocks.
    _create(client, "Petra Einfach")
    _create(client, "Petra Einfach")

    # Explicit override after the user saw the candidates: allowed, deliberately.
    overridden = client.post(
        "/api/v1/patients",
        json={
            "display_name": "Peter Doppelt",
            "date_of_birth": _DOB,
            "allow_duplicate": True,
        },
    )
    assert overridden.status_code == 201, overridden.text


def test_create_records_onboarding_consents_atomically(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = login_as(
        client,
        admin_session,
        email="onb-consent@synthetic.example",
        tenant_name="Consent Onboarding Clinic",
        tenant_slug="consent-onboarding-clinic",
        role=Role.ASSISTANT,
    )
    created = _create(
        client,
        "Carla Einwillig",
        date_of_birth=_DOB,
        consents=[
            {"purpose": "report_release", "channel": "in_person"},
            {"purpose": "data_source_connect", "channel": "in_person"},
        ],
    )
    pid = uuid.UUID(created["id"])

    events = (
        admin_session.execute(
            select(ConsentEvent)
            .where(ConsentEvent.patient_id == pid)
            .order_by(ConsentEvent.purpose)
        )
        .scalars()
        .all()
    )
    assert [(e.purpose.value, e.event_type.value) for e in events] == [
        ("data_source_connect", "granted"),
        ("report_release", "granted"),
    ]
    # Attributable: who recorded it, over which channel, with the Alpha text version.
    assert all(e.recorded_by_user_id == user.id for e in events)
    assert all(e.channel == "in_person" for e in events)
    assert all(e.consent_text_version == "synthetic-v1" for e in events)

    # Each grant audited with the purpose only; the create itself audited as before.
    audit = (
        admin_session.execute(
            select(AuditEvent).where(
                AuditEvent.target_id == pid, AuditEvent.action == "consent.granted"
            )
        )
        .scalars()
        .all()
    )
    assert sorted(e.detail["purpose"] for e in audit) == [
        "data_source_connect",
        "report_release",
    ]
    assert all(e.actor_user_id == user.id for e in audit)
    created_audit = (
        admin_session.execute(
            select(AuditEvent).where(
                AuditEvent.target_id == pid, AuditEvent.action == "patient.create"
            )
        )
        .scalars()
        .one()
    )
    assert created_audit.actor_user_id == user.id


def test_create_rejects_implausible_input_without_side_effects(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="onb-valid@synthetic.example",
        tenant_name="Validation Clinic",
        tenant_slug="validation-clinic",
        role=Role.CLINICIAN,
    )
    # Future date of birth, pre-1900 date of birth, blank name, repeated purpose: all 422.
    for payload in (
        {"display_name": "Zukunft Kind", "date_of_birth": "2999-01-01"},
        {"display_name": "Uralt Person", "date_of_birth": "1899-12-31"},
        {"display_name": "   "},
        {
            "display_name": "Doppel Zweck",
            "consents": [
                {"purpose": "report_release", "channel": "in_person"},
                {"purpose": "report_release", "channel": "in_person"},
            ],
        },
    ):
        resp = client.post("/api/v1/patients", json=payload)
        assert resp.status_code == 422, (payload, resp.text)

    # None of the rejected attempts persisted anything.
    patients = admin_session.execute(
        select(Patient).where(Patient.tenant_id == tenant.id)
    ).scalars()
    assert list(patients) == []


def test_duplicate_check_is_read_gated_create_stays_care_staff(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="onb-authz-a@synthetic.example",
        tenant_name="Authz Onboarding Clinic",
        tenant_slug="authz-onboarding-clinic",
        role=Role.ASSISTANT,
    )
    _create(client, "Sichtbar Person", date_of_birth=_DOB)

    # The medical director reviews (read staff): may probe, may NOT create.
    switch_role(
        client,
        admin_session,
        email="onb-authz-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    probe = _probe(client, "Sichtbar Person", date_of_birth=_DOB)
    assert probe["has_strong_match"] is True
    denied = client.post("/api/v1/patients", json={"display_name": "MD Versuch"})
    assert denied.status_code == 403, denied.text
