"""Patient invitations P1/P2 (docs/notes/0010): mint → redeem → consent, fail-closed.

The invitation is a single-use, TTL'd, revocable credential; redeeming it appends the
GRANTED report_release consent event the P0 release gate consumes — in one transaction.
Every non-redeemable state is the SAME 404 (no oracle), each denial audited. Synthetic
identities only; real-patient use stays BLOCKED behind the register's pending gates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.invitations.models import PatientInvitation
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


def _invite(client, slug: str) -> tuple[str, str, dict]:  # type: ignore[no-untyped-def, type-arg]
    pid = client.post("/api/v1/patients", json={"display_name": f"Inv {slug}"}).json()["id"]
    resp = client.post(f"/api/v1/patients/{pid}/invitations")
    assert resp.status_code == 201, resp.text
    return pid, resp.json()["invitation_token"], resp.json()


def test_invite_redeem_unlocks_release_end_to_end(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="inv-assistant@synthetic.example",
        tenant_name="Invite Clinic",
        tenant_slug="invite-clinic",
        role=Role.ASSISTANT,  # inviting is staff-wide provisioning
    )
    pid, token, body = _invite(client, "a")
    assert body["invitation_url"].startswith("http")
    assert token in body["invitation_url"]

    # Token hygiene: only the hash is stored; the audit detail never carries the token.
    row = admin_session.execute(select(PatientInvitation)).scalars().one()
    assert row.token_hash != token and token not in row.token_hash
    assert row.is_synthetic is True
    create_event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "invitation.create"))
        .scalars()
        .one()
    )
    assert token not in str(create_event.detail)

    # Patient-side redeem: NO staff session, token in the POST body.
    anon = client.__class__(client.app, base_url=str(client.base_url))
    redeemed = anon.post(
        "/api/v1/invitations/redeem", json={"tenant": str(tenant.id), "token": token}
    )
    assert redeemed.status_code == 200, redeemed.text
    assert redeemed.json() == {"status": "redeemed", "purpose": "report_release"}

    # Exactly one GRANTED consent event, unattributed to a staff user (token identity).
    consent = admin_session.execute(select(ConsentEvent)).scalars().one()
    assert consent.event_type.value == "granted"
    assert consent.purpose.value == "report_release"
    assert consent.recorded_by_user_id is None
    assert consent.channel == "synthetic_invite_redeem"

    # Single-use: a second redeem is the same neutral 404 and appends NO second grant.
    again = anon.post("/api/v1/invitations/redeem", json={"tenant": str(tenant.id), "token": token})
    assert again.status_code == 404
    assert len(admin_session.execute(select(ConsentEvent)).scalars().all()) == 1

    # The consent the redeem wrote unlocks the full gate: import → draft → approve → release.
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    rid = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    switch_role(
        client,
        admin_session,
        email="inv-clin@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email="inv-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{rid}/release").status_code == 200


def test_redeem_failure_modes_are_one_neutral_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="inv2@synthetic.example",
        tenant_name="Invite Clinic 2",
        tenant_slug="invite-clinic-2",
        role=Role.CLINICIAN,
    )
    _pid, token, body = _invite(client, "b")
    anon = client.__class__(client.app, base_url=str(client.base_url))

    # Unknown token.
    r1 = anon.post("/api/v1/invitations/redeem", json={"tenant": str(tenant.id), "token": "nope"})
    # Wrong tenant for a valid token (cross-tenant isolation).
    r2 = anon.post("/api/v1/invitations/redeem", json={"tenant": str(uuid.uuid4()), "token": token})
    assert (r1.status_code, r2.status_code) == (404, 404)
    assert r1.json() == r2.json()  # identical body — no oracle

    # Revoked → 404.
    assert client.post(f"/api/v1/invitations/{body['invitation_id']}/revoke").status_code == 200
    r3 = anon.post("/api/v1/invitations/redeem", json={"tenant": str(tenant.id), "token": token})
    assert r3.status_code == 404

    # Expired → 404 (age the row via the admin session).
    _pid2, token2, _body2 = _invite(client, "b2")
    row = (
        admin_session.execute(
            select(PatientInvitation).order_by(PatientInvitation.created_at.desc())
        )
        .scalars()
        .first()
    )
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    admin_session.commit()
    r4 = anon.post("/api/v1/invitations/redeem", json={"tenant": str(tenant.id), "token": token2})
    assert r4.status_code == 404

    # Denials are audited as security events. The nonexistent-tenant probe (r2) cannot
    # be attributed — its audit row would violate the tenants FK and the write is
    # deliberately dropped (logged at ERROR); that surface is covered by the identical
    # 404 + the per-IP rate limiter. The other three denials are on record.
    denials = (
        admin_session.execute(
            select(AuditEvent).where(AuditEvent.action == "invitation.redeem_denied")
        )
        .scalars()
        .all()
    )
    assert len(denials) == 3


def test_medical_director_cannot_invite_and_cross_tenant_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="inv3@synthetic.example",
        tenant_name="Invite Clinic 3",
        tenant_slug="invite-clinic-3",
        role=Role.CLINICIAN,
    )
    pid, _token, _body = _invite(client, "c")
    switch_role(
        client,
        admin_session,
        email="inv3-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/patients/{pid}/invitations").status_code == 403

    login_as(
        client,
        admin_session,
        email="inv3-b@synthetic.example",
        tenant_name="Invite Clinic 3B",
        tenant_slug="invite-clinic-3b",
        role=Role.CLINICIAN,
    )
    assert client.post(f"/api/v1/patients/{pid}/invitations").status_code == 404


def test_redeem_is_rate_limited(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = uuid.uuid4()
    anon = client.__class__(client.app, base_url=str(client.base_url))
    for _ in range(30):
        assert (
            anon.post(
                "/api/v1/invitations/redeem", json={"tenant": str(tenant), "token": "guess"}
            ).status_code
            == 404
        )
    blocked = anon.post(
        "/api/v1/invitations/redeem", json={"tenant": str(tenant), "token": "guess"}
    )
    assert blocked.status_code == 429, blocked.text
