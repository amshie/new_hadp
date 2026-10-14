"""The clinic's own settings (Einstellungen, docs/notes/0016 part 3): its profile, and which
consent text versions its records refer to.

Every staff role reads the profile; the owner changes it, and the change records which fields
changed, never their values. A patient reading a released report sees which practice released
it. The consent summary is counts per purpose and text version, of this clinic only.
"""

from __future__ import annotations

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import login_as, switch_role
from tests.test_consent_api import _IMPORT


def _owner(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"clinic-{slug}@synthetic.example",
        tenant_name=f"Clinic {slug}",
        tenant_slug=f"clinic-{slug}",
        role=Role.OWNER,
    )


def test_every_role_reads_the_profile_and_only_the_owner_changes_it(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "profile")
    profile = client.get("/api/v1/clinic-profile").json()
    assert profile == {
        "name": "Clinic profile",
        "address": None,
        "lab_time_zone": "Europe/Berlin",
        "is_synthetic": True,
    }

    changed = client.put(
        "/api/v1/clinic-profile",
        json={"name": "  Praxis am Park  ", "address": "Parkstraße 1\n10115 Berlin"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["name"] == "Praxis am Park"
    assert changed.json()["address"] == "Parkstraße 1\n10115 Berlin"
    # The shell's clinic name follows.
    assert client.get("/api/v1/auth/me").json()["active_tenant_name"] == "Praxis am Park"

    event = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "tenant.profile_changed")
    ).scalar_one()
    assert event.tenant_id == tenant.id
    assert event.detail == {"changed": ["name", "address"]}
    assert "Park" not in str(event.detail)

    # Saving the same again changes nothing and records nothing new.
    client.put(
        "/api/v1/clinic-profile",
        json={"name": "Praxis am Park", "address": "Parkstraße 1\n10115 Berlin"},
    )
    events = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "tenant.profile_changed")
    ).all()
    assert len(events) == 1
    # A blank address is no address.
    assert (
        client.put(
            "/api/v1/clinic-profile", json={"name": "Praxis am Park", "address": "  "}
        ).json()["address"]
        is None
    )

    for role, email in (
        (Role.CLINICIAN, "clinic-profile-c@synthetic.example"),
        (Role.MEDICAL_DIRECTOR, "clinic-profile-m@synthetic.example"),
        (Role.ASSISTANT, "clinic-profile-a@synthetic.example"),
    ):
        switch_role(client, admin_session, email=email, tenant=tenant, role=role)
        assert client.get("/api/v1/clinic-profile").json()["name"] == "Praxis am Park"
        refused = client.put("/api/v1/clinic-profile", json={"name": "Taken over"})
        assert refused.status_code == 403
    admin_session.expire_all()
    assert admin_session.get(Tenant, tenant.id).name == "Praxis am Park"


def test_a_profile_needs_a_name_and_a_short_address(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "bounds")
    assert client.put("/api/v1/clinic-profile", json={"name": "   "}).status_code == 422
    too_long = client.put("/api/v1/clinic-profile", json={"name": "P", "address": "x" * 301})
    assert too_long.status_code == 422
    assert "x" * 50 not in too_long.text


def test_a_profile_is_the_clinics_own(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "mine")
    client.put("/api/v1/clinic-profile", json={"name": "Mine", "address": "Here"})
    _owner(client, admin_session, "theirs")
    assert client.get("/api/v1/clinic-profile").json()["name"] == "Clinic theirs"


def test_the_patient_sees_which_practice_released_the_report(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="clinic-view-c@synthetic.example",
        tenant_name="Clinic View",
        tenant_slug="clinic-view",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "View Patient"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    client.post(
        f"/api/v1/patients/{pid}/consents",
        json={"purpose": "report_release", "channel": "in_person"},
    )
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email="clinic-view-o@synthetic.example",
        tenant=tenant,
        role=Role.OWNER,
    )
    client.put("/api/v1/clinic-profile", json={"name": "Clinic View", "address": "Weg 2"})
    switch_role(
        client,
        admin_session,
        email="clinic-view-m@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    token = client.post(f"/api/v1/reports/{rid}/release").json()["patient_access_token"]
    view = client.post(
        "/api/v1/patient-view", json={"tenant": str(tenant.id), "token": token}
    ).json()
    assert view["clinic"] == {"name": "Clinic View", "address": "Weg 2"}


def test_consent_texts_are_counted_per_purpose_and_version(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="clinic-consent@synthetic.example",
        tenant_name="Clinic Consent",
        tenant_slug="clinic-consent",
        role=Role.ASSISTANT,
    )
    empty = client.get("/api/v1/consent-texts").json()
    assert empty == {"current_version": "synthetic-v1", "counts": []}

    first = client.post("/api/v1/patients", json={"display_name": "Consent One"}).json()["id"]
    second = client.post("/api/v1/patients", json={"display_name": "Consent Two"}).json()["id"]
    for pid in (first, second):
        client.post(
            f"/api/v1/patients/{pid}/consents",
            json={"purpose": "report_release", "channel": "in_person"},
        )
    client.post(
        f"/api/v1/patients/{first}/consents",
        json={"purpose": "analytics", "channel": "in_person"},
    )
    withdrawn = client.post(
        f"/api/v1/patients/{first}/consents/withdraw",
        json={"purpose": "analytics", "channel": "in_person"},
    )
    assert withdrawn.status_code in (200, 201), withdrawn.text

    counts = {
        (c["purpose"], c["consent_text_version"]): (c["granted"], c["withdrawn"])
        for c in client.get("/api/v1/consent-texts").json()["counts"]
    }
    assert counts == {
        ("analytics", "synthetic-v1"): (1, 1),
        ("report_release", "synthetic-v1"): (2, 0),
    }

    # Another clinic counts none of these.
    login_as(
        client,
        admin_session,
        email="clinic-consent-b@synthetic.example",
        tenant_name="Clinic Consent B",
        tenant_slug="clinic-consent-b",
        role=Role.ASSISTANT,
    )
    assert client.get("/api/v1/consent-texts").json()["counts"] == []
