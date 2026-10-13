"""What a clinic's trail takes from callers without a session.

The patient view and the two invitation redemptions record a wrong token under the clinic
the request names. The limit per client address bounds one address, not a caller: with the
web server passing client addresses on, anyone with many addresses could write a row into any
clinic's append-only trail with every request. So the trail takes 30 refusals per surface,
clinic and minute, then one entry that says recording stops for the rest of that minute — and
the requests are still answered, so nobody's guessing locks a clinic's patients out
(security/rate_limit.py::refusal_recording).

Synthetic clinics and documentation addresses (RFC 5737) only.
"""

from __future__ import annotations

import uuid
from collections import Counter

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from sqlalchemy import select

from hadp_api.config import get_settings
from hadp_api.errors import ServiceUnavailable
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.models import Tenant
from hadp_api.security import rate_limit
from hadp_api.security.rate_limit import (
    REFUSAL_WINDOW_SECONDS,
    REFUSALS_RECORDED,
    refusal_recording,
)
from tests.helpers import login_as, provision_staff

WEB = "10.20.0.5"  # the web server, as the API sees it
_NOBODY = {"display_name": "Synthetic Nobody", "email": "nobody@synthetic.example"}

# (path, what the body holds besides clinic and token, the refusal, the entry that ends them)
PATIENT_VIEW = (
    "/api/v1/patient-view",
    {},
    "report.patient_view_denied",
    "report.patient_view_denials_unrecorded",
)
INVITATION = (
    "/api/v1/invitations/redeem",
    {},
    "invitation.redeem_denied",
    "invitation.redeem_denials_unrecorded",
)
STAFF_INVITATION = (
    "/api/v1/staff-invitations/redeem",
    _NOBODY,
    "staff_invite.redeem_denied",
    "staff_invite.redeem_denials_unrecorded",
)
SURFACES = [PATIENT_VIEW, INVITATION, STAFF_INVITATION]


def _clinic(admin_session, slug: str) -> Tenant:  # type: ignore[no-untyped-def]
    _owner, tenant = provision_staff(
        admin_session,
        email=f"owner-{slug}@synthetic.example",
        tenant_name=f"Refusals {slug}",
        tenant_slug=f"refusals-{slug}",
        role=Role.OWNER,
    )
    return tenant


def _web(client) -> TestClient:  # type: ignore[no-untyped-def]
    """The web server calling the API, without anyone's session."""
    return TestClient(client.app, base_url=str(client.base_url), client=(WEB, 50000))


def _refuse(web: TestClient, surface: tuple, tenant_id: uuid.UUID, caller: int) -> int:  # type: ignore[type-arg]
    """One wrong token for the clinic, sent by the caller-th client address."""
    path, extra, _denied, _marker = surface
    resp = web.post(
        path,
        json={"tenant": str(tenant_id), "token": "guess", **extra},
        headers={"x-forwarded-for": f"198.51.100.{caller + 1}"},
    )
    return resp.status_code


def _trail(admin_session, tenant_id: uuid.UUID) -> Counter[str]:  # type: ignore[no-untyped-def]
    actions = admin_session.execute(
        select(AuditEvent.action).where(AuditEvent.tenant_id == tenant_id)
    ).scalars()
    return Counter(actions)


def _throttled(admin_session) -> int:  # type: ignore[no-untyped-def]
    events = admin_session.execute(
        select(AuditEvent.id).where(AuditEvent.action == "rate_limited")
    ).scalars()
    return len(list(events))


@pytest.mark.parametrize("surface", SURFACES, ids=["patient-view", "invitation", "staff-invite"])
def test_a_clinics_trail_takes_thirty_refusals_a_minute_whoever_sends_them(  # type: ignore[no-untyped-def]
    client,
    admin_session,
    trust_proxies,
    surface: tuple,  # type: ignore[type-arg]
) -> None:
    _path, _extra, denied, marker = surface
    trust_proxies(WEB)
    tenant = _clinic(admin_session, "many")
    web = _web(client)

    # 45 callers, one wrong token each: no address comes near its own limit.
    answers = [_refuse(web, surface, tenant.id, caller) for caller in range(45)]

    # Every one of them is answered, and the same way.
    assert answers == [404] * 45
    assert _throttled(admin_session) == 0
    assert _trail(admin_session, tenant.id) == {denied: REFUSALS_RECORDED, marker: 1}
    ended = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == marker)
    ).scalar_one()
    assert ended.detail == {"recorded": 30, "window_seconds": 60}
    assert ended.tenant_id == tenant.id and ended.actor_user_id is None


def test_a_clinics_own_invitation_is_still_redeemed_after_recording_stopped(  # type: ignore[no-untyped-def]
    client, admin_session, trust_proxies
) -> None:
    """The cap is on what is written, not on what is answered."""
    trust_proxies(WEB)
    _user, tenant = login_as(
        client,
        admin_session,
        email="refusals-assistant@synthetic.example",
        tenant_name="Refusals Open",
        tenant_slug="refusals-open",
        role=Role.ASSISTANT,
    )
    patient = client.post("/api/v1/patients", json={"display_name": "Refusal Case (synthetic)"})
    assert patient.status_code == 201, patient.text
    invitation = client.post(f"/api/v1/patients/{patient.json()['id']}/invitations")
    assert invitation.status_code == 201, invitation.text
    web = _web(client)
    for caller in range(40):
        assert _refuse(web, INVITATION, tenant.id, caller) == 404
    assert _trail(admin_session, tenant.id)["invitation.redeem_denials_unrecorded"] == 1

    redeemed = web.post(
        "/api/v1/invitations/redeem",
        json={"tenant": str(tenant.id), "token": invitation.json()["invitation_token"]},
        headers={"x-forwarded-for": "203.0.113.50"},
    )

    assert redeemed.status_code == 200, redeemed.text
    trail = _trail(admin_session, tenant.id)
    assert trail["invitation.redeemed"] == 1
    assert trail["invitation.redeem_denied"] == REFUSALS_RECORDED


def test_one_clinics_refusals_do_not_use_up_anothers(client, admin_session, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)
    first = _clinic(admin_session, "first")
    second = _clinic(admin_session, "second")
    web = _web(client)
    for caller in range(REFUSALS_RECORDED + 5):
        _refuse(web, PATIENT_VIEW, first.id, caller)

    assert _refuse(web, PATIENT_VIEW, second.id, 100) == 404

    assert _trail(admin_session, second.id) == {"report.patient_view_denied": 1}


def test_one_surfaces_refusals_do_not_use_up_anothers(client, admin_session, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)
    tenant = _clinic(admin_session, "surfaces")
    web = _web(client)
    for caller in range(REFUSALS_RECORDED + 5):
        _refuse(web, PATIENT_VIEW, tenant.id, caller)

    assert _refuse(web, INVITATION, tenant.id, 100) == 404
    assert _refuse(web, STAFF_INVITATION, tenant.id, 101) == 404

    assert _trail(admin_session, tenant.id) == {
        "report.patient_view_denied": REFUSALS_RECORDED,
        "report.patient_view_denials_unrecorded": 1,
        "invitation.redeem_denied": 1,
        "staff_invite.redeem_denied": 1,
    }


def test_recording_starts_again_with_the_next_window(client, admin_session, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)
    tenant = _clinic(admin_session, "window")
    web = _web(client)
    for caller in range(REFUSALS_RECORDED + 5):
        _refuse(web, PATIENT_VIEW, tenant.id, caller)
    store = redis_lib.Redis.from_url(get_settings().redis_url)
    counter = f"rl-recorded:patient_view:{tenant.id}"
    # The count ends by itself: it was given a window when it began.
    assert 0 < store.ttl(counter) <= REFUSAL_WINDOW_SECONDS

    store.delete(counter)  # the window is over
    assert _refuse(web, PATIENT_VIEW, tenant.id, 100) == 404

    assert _trail(admin_session, tenant.id) == {
        "report.patient_view_denied": REFUSALS_RECORDED + 1,
        "report.patient_view_denials_unrecorded": 1,
    }


def test_one_address_is_stopped_by_its_own_limit_before_recording_stops(  # type: ignore[no-untyped-def]
    client, admin_session
) -> None:
    """The two bounds are separate: 30 a minute per address, 30 recorded a minute per clinic.
    A single caller reaches the first — it is refused, and that is what is recorded."""
    tenant = _clinic(admin_session, "single")
    answers = [
        client.post(
            "/api/v1/patient-view", json={"tenant": str(tenant.id), "token": "guess"}
        ).status_code
        for _ in range(REFUSALS_RECORDED + 3)
    ]

    assert answers == [404] * 30 + [429] * 3
    assert _trail(admin_session, tenant.id) == {"report.patient_view_denied": REFUSALS_RECORDED}
    assert _throttled(admin_session) == 1  # once for the window, without a clinic


def test_without_the_count_a_refusal_is_not_recorded_and_the_answer_says_so(  # type: ignore[no-untyped-def]
    client, admin_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed, like the limiter: if the count of recorded refusals cannot be read, nothing
    is written — and the caller is told the service is unavailable, not that the link is wrong."""
    tenant = _clinic(admin_session, "outage")
    count = rate_limit._count

    def count_unless_recording(name: str, window_seconds: int) -> int:
        if name.startswith("rl-recorded:"):
            raise ServiceUnavailable("rate limiting unavailable")
        return count(name, window_seconds)

    monkeypatch.setattr(rate_limit, "_count", count_unless_recording)

    resp = client.post("/api/v1/patient-view", json={"tenant": str(tenant.id), "token": "guess"})

    assert resp.status_code == 503, resp.text
    assert _trail(admin_session, tenant.id) == {}


def test_the_verdicts_of_one_window() -> None:
    """The first 30 each, the 31st by the entry that ends them, the rest not at all."""
    tenant_id = uuid.uuid4()
    verdicts = [refusal_recording(surface="patient_view", tenant_id=tenant_id) for _ in range(34)]

    assert verdicts == ["each"] * 30 + ["stops"] + ["stopped"] * 3
    # Another clinic, another surface: their own count.
    assert refusal_recording(surface="patient_view", tenant_id=uuid.uuid4()) == "each"
    assert refusal_recording(surface="invitation.redeem", tenant_id=tenant_id) == "each"
