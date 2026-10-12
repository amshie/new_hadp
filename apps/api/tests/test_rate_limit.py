"""Rate limiting (P-pre-1, docs/notes/0010): fixed-window, Redis-backed, fail-closed.

The login and public patient-view token surfaces are throttled per client IP; the
(limit+1)-th call inside the window is a 429 and emits an audited `rate_limited`
security event on an independent transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login_as, provision_staff, switch_role


def test_login_is_rate_limited_per_ip(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    provision_staff(
        admin_session,
        email="rl@synthetic.example",
        tenant_name="RL Clinic",
        tenant_slug="rl-clinic",
        role=Role.CLINICIAN,
    )
    # Limit is 10/min per IP; mixed success/failure attempts all count.
    for i in range(10):
        email = "rl@synthetic.example" if i % 2 == 0 else f"ghost-{i}@synthetic.example"
        resp = client.post("/api/v1/auth/dev-login", json={"email": email})
        assert resp.status_code in (200, 401), resp.text
    blocked = client.post("/api/v1/auth/dev-login", json={"email": "rl@synthetic.example"})
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["error"]["code"] == "too_many_requests"

    event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "rate_limited"))
        .scalars()
        .one()
    )
    assert event.detail == {"action": "auth.dev_login"}


def test_patient_view_token_surface_is_rate_limited(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = uuid.uuid4()
    # 30/min per IP on the public, brute-forceable token surface: the guesses 404,
    # the 31st attempt is throttled before touching the database.
    for _ in range(30):
        resp = client.post("/api/v1/patient-view", json={"tenant": str(tenant), "token": "guess"})
        assert resp.status_code == 404
    blocked = client.post("/api/v1/patient-view", json={"tenant": str(tenant), "token": "guess"})
    assert blocked.status_code == 429, blocked.text
    events = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "rate_limited"))
        .scalars()
        .all()
    )
    assert any(e.detail == {"action": "patient_view"} for e in events)


def test_drafting_a_report_is_rate_limited_per_user(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A draft is a new report, or a new version, that is kept: 30 a minute per user, for
    generating and for re-drafting together."""
    _, tenant = login_as(
        client,
        admin_session,
        email="draft-rl@synthetic.example",
        tenant_name="Draft RL Clinic",
        tenant_slug="draft-rl",
        role=Role.CLINICIAN,
    )
    patient = client.post("/api/v1/patients", json={"display_name": "Draft Limit (synthetic)"})
    assert patient.status_code == 201, patient.text
    drafts = f"/api/v1/patients/{patient.json()['id']}/reports"

    # The patient has no published value, so each call is refused on its merits (422) —
    # and counts: the limit bounds the attempts, whatever they would have produced.
    for _ in range(30):
        assert client.post(drafts).status_code == 422
    blocked = client.post(drafts)
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["error"]["code"] == "too_many_requests"
    # The same counter: a new draft version is a draft.
    assert client.post(f"/api/v1/reports/{uuid.uuid4()}/redraft").status_code == 429

    events = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "rate_limited"))
        .scalars()
        .all()
    )
    assert [e.detail for e in events] == [{"action": "report.draft"}] * 2

    # Per user: a colleague in the same clinic is not held back by it.
    switch_role(
        client,
        admin_session,
        email="draft-rl-colleague@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert client.post(drafts).status_code == 422


def test_a_role_that_may_not_draft_does_not_use_up_the_limit(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Authorization comes first: a refused role is a 403 every time, never a 429."""
    login_as(
        client,
        admin_session,
        email="draft-rl-md@synthetic.example",
        tenant_name="Draft RL MD Clinic",
        tenant_slug="draft-rl-md",
        role=Role.MEDICAL_DIRECTOR,
    )
    for _ in range(32):
        resp = client.post(f"/api/v1/patients/{uuid.uuid4()}/reports")
        assert resp.status_code == 403, resp.text
