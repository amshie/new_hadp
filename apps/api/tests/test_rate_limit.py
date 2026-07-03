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
from tests.helpers import provision_staff


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
