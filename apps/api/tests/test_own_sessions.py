"""One's own sessions (Einstellungen › Sicherheit & Sitzungen, docs/notes/0016 part 3).

A person sees their own sessions only — when each began, whether it still runs, the clinic
last chosen in it — and can end every other one. No address and no device are recorded, so
none is shown. Ending the others is recorded without a clinic, like signing in and out.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from hadp_api.main import app
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.identity.models import AuthSession
from tests.helpers import login, login_as, provision_staff


def test_sessions_require_a_session(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/auth/sessions").status_code == 401
    assert client.post("/api/v1/auth/sessions/end-others").status_code in (401, 403)


def test_a_person_sees_their_own_sessions_and_ends_the_others(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = login_as(
        client,
        admin_session,
        email="sessions-a@synthetic.example",
        tenant_name="Sessions A",
        tenant_slug="sessions-a",
        role=Role.CLINICIAN,
    )
    # The same person on a second device, and someone else.
    with TestClient(app) as other_device:
        login(other_device, "sessions-a@synthetic.example")
    provision_staff(
        admin_session,
        email="sessions-b@synthetic.example",
        tenant_name="Sessions B",
        tenant_slug="sessions-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as someone_else:
        login(someone_else, "sessions-b@synthetic.example")

    body = client.get("/api/v1/auth/sessions").json()
    assert body["sign_in"] == "dev"
    sessions = body["sessions"]
    assert len(sessions) == 2
    assert all(s["state"] == "active" for s in sessions)
    current = [s for s in sessions if s["current"]]
    assert len(current) == 1
    assert current[0]["clinic"] == "Sessions A"
    assert {s["clinic"] for s in sessions if not s["current"]} == {None}
    # Nothing that would identify a device or a place.
    assert set(sessions[0]) == {
        "id",
        "started_at",
        "expires_at",
        "ended_at",
        "state",
        "current",
        "clinic",
    }

    ended = client.post("/api/v1/auth/sessions/end-others")
    assert ended.status_code == 200, ended.text
    assert ended.json() == {"ended": 1}
    after = client.get("/api/v1/auth/sessions").json()["sessions"]
    assert sorted(s["state"] for s in after) == ["active", "ended"]
    assert next(s for s in after if s["state"] == "ended")["ended_at"] is not None
    # This session still works; the other one is over; someone else's is untouched.
    assert client.get("/api/v1/auth/me").status_code == 200
    others = (
        admin_session.execute(select(AuthSession).where(AuthSession.user_id != user.id))
        .scalars()
        .all()
    )
    assert others and all(s.revoked_at is None for s in others)

    event = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "auth.sessions_ended")
    ).scalar_one()
    assert event.actor_user_id == user.id
    assert event.tenant_id is None
    assert event.detail == {"count": 1}
    # Nothing left to end.
    assert client.post("/api/v1/auth/sessions/end-others").json() == {"ended": 0}
