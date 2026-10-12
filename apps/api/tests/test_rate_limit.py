"""Rate limiting (P-pre-1, docs/notes/0010): fixed-window, Redis-backed, fail-closed.

The login and public patient-view token surfaces are throttled per client IP; the
(limit+1)-th call inside the window is a 429 and emits an audited `rate_limited`
security event on an independent transaction.
"""

from __future__ import annotations

import uuid

import redis as redis_lib
from sqlalchemy import select

from hadp_api.config import get_settings
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.security.rate_limit import check_rate_limit
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
    for _ in range(5):
        assert client.post(drafts).status_code == 429

    # Refused every time, recorded once per window: the limit bounds what a client that keeps
    # trying can write — its drafts, and the trail of its refusals.
    events = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "rate_limited"))
        .scalars()
        .all()
    )
    assert [e.detail for e in events] == [{"action": "report.draft"}]

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
    director, _tenant = login_as(
        client,
        admin_session,
        email="draft-rl-md@synthetic.example",
        tenant_name="Draft RL MD Clinic",
        tenant_slug="draft-rl-md",
        role=Role.MEDICAL_DIRECTOR,
    )
    for _attempt in range(32):
        assert client.post(f"/api/v1/patients/{uuid.uuid4()}/reports").status_code == 403
        assert client.post(f"/api/v1/reports/{uuid.uuid4()}/redraft").status_code == 403
    # Nothing was counted for her at all.
    counters = redis_lib.Redis.from_url(get_settings().redis_url)
    assert counters.exists(f"rl:report.draft:{director.id}") == 0


def test_a_counter_that_lost_its_expiry_is_given_its_window_again() -> None:
    """INCR and EXPIRE are two commands. A key whose EXPIRE never arrived would count for
    ever and refuse that caller for good — the limiter re-arms it instead."""
    counters = redis_lib.Redis.from_url(get_settings().redis_url)
    name = "rl:test.expiry:synthetic-caller"
    counters.set(name, 3)  # a counter mid-window, without an expiry
    assert counters.ttl(name) == -1

    check_rate_limit(action="test.expiry", key="synthetic-caller", limit=10, window_seconds=60)

    assert int(counters.get(name)) == 4
    assert 0 < counters.ttl(name) <= 60


def test_a_window_starts_with_its_first_call_and_is_not_extended_by_later_ones() -> None:
    counters = redis_lib.Redis.from_url(get_settings().redis_url)
    name = "rl:test.window:synthetic-caller"

    check_rate_limit(action="test.window", key="synthetic-caller", limit=10, window_seconds=60)
    assert 0 < counters.ttl(name) <= 60
    counters.expire(name, 20)  # as if 40 seconds had passed
    check_rate_limit(action="test.window", key="synthetic-caller", limit=10, window_seconds=60)

    assert int(counters.get(name)) == 2
    assert 0 < counters.ttl(name) <= 20
