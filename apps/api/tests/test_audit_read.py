"""The clinic reads its own audit trail (go-live plan A9).

OWNER only; exactly the events recorded for that clinic — never another clinic's, and never
the tenant-less events (sign-ins, denials before a clinic is selected) that row-level security
would let through; newest first, paged by an opaque cursor without skipping or repeating an
event; filtered by category, actor, target and time; and the read is itself recorded.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select, text

from hadp_api.config import get_settings
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login, login_as, select_tenant, switch_role

URL = "/api/v1/audit-events"


def _owner(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"owner-{slug}@synthetic.example",
        tenant_name=f"Audit {slug}",
        tenant_slug=f"audit-{slug}",
        role=Role.OWNER,
    )


def _event(admin_session, tenant_id, action: str, **fields: object) -> AuditEvent:  # type: ignore[no-untyped-def]
    event = AuditEvent(tenant_id=tenant_id, action=action, detail={}, **fields)
    admin_session.add(event)
    admin_session.flush()
    return event


def _walk(client, **params: object) -> list[dict]:  # type: ignore[no-untyped-def, type-arg]
    """Read every page; fail on a repeated event."""
    items: list[dict] = []  # type: ignore[type-arg]
    cursor: str | None = None
    for _ in range(100):
        query = {**params, **({"cursor": cursor} if cursor else {})}
        resp = client.get(URL, params=query)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items.extend(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "an event was returned twice"
    return items


def test_an_owner_reads_the_clinics_own_trail_newest_first(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _owner(client, admin_session, "own")
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic Audit"}).json()["id"]

    body = client.get(URL).json()

    actions = [i["action"] for i in body["items"]]
    assert actions[0] == "patient.create"
    assert "tenant.select" in actions
    created = body["items"][0]
    assert (created["target_type"], created["target_id"]) == ("patient", pid)
    # Who acted, by name: a colleague in the reader's own clinic.
    assert created["actor"] == {
        "user_id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
    }
    assert body["next_cursor"] is None
    # Exactly this clinic's events — compared with what the table holds for it.
    stored = admin_session.execute(
        select(AuditEvent.id).where(
            AuditEvent.tenant_id == tenant.id, AuditEvent.action != "audit.read"
        )
    ).scalars()
    assert {i["id"] for i in body["items"]} == {str(i) for i in stored}


def test_reading_the_trail_is_itself_recorded(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _owner(client, admin_session, "meta")
    target = uuid.uuid4()
    first = client.get(
        URL, params={"category": "patient", "target_id": str(target), "exclude_reads": "true"}
    )
    assert first.status_code == 200

    read = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "audit.read")
    ).scalar_one()
    assert (read.tenant_id, read.actor_user_id) == (tenant.id, user.id)
    # Which filters were set — never their values (the target id is not in the event).
    assert read.detail == {
        "count": 0,
        "category": "patient",
        "by_actor": False,
        "by_target": True,
        "by_time": False,
        "exclude_reads": True,
        "continued": False,
    }
    assert str(target) not in str(read.detail)
    # And the next read shows it.
    assert client.get(URL).json()["items"][0]["action"] == "audit.read"


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR])
def test_only_the_owner_reads_the_trail(client, admin_session, role: Role) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, f"role-{role.value}")
    switch_role(
        client, admin_session, email=f"{role.value}@synthetic.example", tenant=tenant, role=role
    )

    denied = client.get(URL)

    assert denied.status_code == 403
    assert "items" not in denied.text
    recorded = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "authz.denied")
    ).scalar_one()
    assert recorded.detail == {"reason": "role_not_permitted", "attempted": "audit.read"}


def test_the_trail_needs_a_session(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get(URL).status_code == 401


def test_another_clinics_events_and_tenantless_events_never_appear(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Row-level security lets a tenant-less event through (it must, for sign-in). Such an event
    is no clinic's: a sign-in or a failed sign-in of ANY user of the platform. The read must not
    return one — and must not return another clinic's either."""
    _other_user, other = _owner(client, admin_session, "other")
    client.post("/api/v1/patients", json={"display_name": "Synthetic Other Clinic"})
    foreign = _event(admin_session, other.id, "report.released")
    tenantless = _event(admin_session, None, "login.failed")
    admin_session.commit()

    _user, tenant = _owner(client, admin_session, "mine")
    items = _walk(client)

    ids = {i["id"] for i in items}
    assert str(foreign.id) not in ids
    assert str(tenantless.id) not in ids
    actions = {i["action"] for i in items}
    assert actions <= {"tenant.select", "audit.read"}, actions
    assert "auth.dev_login" not in actions and "login.failed" not in actions
    # The sign-ins exist, tenant-less — and the APPLICATION ROLE can read them with this clinic
    # selected: the filter in the service is what keeps them out, not row-level security.
    engine = create_engine(get_settings().effective_app_database_url)
    try:
        with engine.connect() as conn:
            conn.execute(
                text("SELECT set_config('app.current_tenant', :t, false)"), {"t": str(tenant.id)}
            )
            let_through = conn.execute(
                text("SELECT action FROM audit_events WHERE tenant_id IS NULL")
            ).scalars()
            assert {"auth.dev_login", "login.failed"} <= set(let_through)
            foreign_rows = conn.execute(
                text("SELECT count(*) FROM audit_events WHERE tenant_id = :o"), {"o": str(other.id)}
            ).scalar_one()
            assert foreign_rows == 0  # another clinic's rows ARE hidden by the policy
    finally:
        engine.dispose()
    # Asking for the other clinic by a filter changes nothing.
    assert _walk(client, target_id=str(uuid.uuid4())) == []
    assert all(i["action"] != "report.released" for i in _walk(client, category="report"))
    assert tenant.id != other.id


def test_paging_neither_skips_nor_repeats_an_event(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Events written in one transaction share a timestamp; new events arrive while someone
    pages. The cursor is a position, not an offset."""
    _user, tenant = _owner(client, admin_session, "paging")
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    expected: list[str] = []
    for minute in range(6):
        for _ in range(5):  # five events per instant
            event = _event(
                admin_session,
                tenant.id,
                "import.run",
                created_at=base + timedelta(minutes=minute),
            )
            expected.append(str(event.id))
    admin_session.commit()

    first = client.get(URL, params={"limit": 7, "category": "import"}).json()
    assert len(first["items"]) == 7 and first["next_cursor"]
    # Appended while paging: newer than everything shown, so it belongs to no later page.
    late = _event(admin_session, tenant.id, "import.run", created_at=base + timedelta(hours=1))
    admin_session.commit()
    rest: list[dict] = []  # type: ignore[type-arg]
    cursor = first["next_cursor"]
    while cursor:
        page = client.get(URL, params={"limit": 7, "category": "import", "cursor": cursor}).json()
        rest.extend(page["items"])
        cursor = page["next_cursor"]

    seen = [i["id"] for i in first["items"] + rest]
    assert len(seen) == len(set(seen)) == 30
    assert set(seen) == set(expected)
    assert str(late.id) not in seen
    # Newest first, and a stable order inside one instant (by id).
    stamps = [i["occurred_at"] for i in first["items"] + rest]
    assert stamps == sorted(stamps, reverse=True)
    same_instant = [i["id"] for i in first["items"] + rest if i["occurred_at"] == stamps[0]]
    assert same_instant == sorted(same_instant, reverse=True)


def test_filters(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _owner(client, admin_session, "filters")
    patient, other_patient = uuid.uuid4(), uuid.uuid4()
    colleague = uuid.uuid4()
    day = datetime(2026, 3, 10, 9, tzinfo=UTC)
    rows = [
        ("patient.read", patient, user.id, day),
        ("patient.create", patient, user.id, day + timedelta(hours=1)),
        ("patient.list", None, user.id, day + timedelta(hours=2)),
        ("patient_view", other_patient, None, day + timedelta(hours=3)),
        ("report.patient_view", patient, None, day + timedelta(days=1)),
        ("report.released", patient, None, day + timedelta(days=2)),
        ("rate_limited", None, None, day + timedelta(days=3)),
    ]
    for action, target, actor, at in rows:
        _event(
            admin_session,
            tenant.id,
            action,
            target_id=target,
            target_type="patient" if target else None,
            actor_user_id=actor,
            created_at=at,
        )
    admin_session.commit()
    window = {"since": "2026-03-01T00:00:00Z", "until": "2026-04-01T00:00:00Z"}

    def actions(**params: object) -> list[str]:
        return sorted(i["action"] for i in _walk(client, **window, **params))

    # A category is the part before the first dot — "patient" is not "patient_view".
    assert actions(category="patient") == ["patient.create", "patient.list", "patient.read"]
    assert actions(category="report") == ["report.patient_view", "report.released"]
    assert actions(category="rate_limited") == ["rate_limited"]
    assert actions(category="patient_view") == ["patient_view"]
    # "_" is a letter here, not a wildcard.
    assert actions(category="patien_") == []
    # Staff reads and listings are the bulk of a trail; a patient opening a report is not one.
    assert actions(exclude_reads="true") == [
        "patient.create",
        "patient_view",
        "rate_limited",
        "report.patient_view",
        "report.released",
    ]
    assert actions(target_id=str(patient)) == [
        "patient.create",
        "patient.read",
        "report.patient_view",
        "report.released",
    ]
    assert actions(actor_user_id=str(user.id)) == ["patient.create", "patient.list", "patient.read"]
    assert actions(actor_user_id=str(colleague)) == []
    # since is inclusive, until exclusive.
    one_day = {"since": "2026-03-10T00:00:00Z", "until": "2026-03-11T09:00:00Z"}
    assert sorted(i["action"] for i in _walk(client, **one_day)) == [
        "patient.create",
        "patient.list",
        "patient.read",
        "patient_view",
    ]
    # An event nobody signed in caused has no actor.
    released = next(i for i in _walk(client, **window) if i["action"] == "report.released")
    assert released["actor"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"cursor": "not-a-cursor"},
        {"cursor": "MjAyNi0wMS0wMVQxMjowMDowMHxub3QtYS11dWlk"},  # "2026-01-01T12:00:00|not-a-uuid"
        {"limit": 0},
        {"limit": 201},
        {"category": "Report"},
        {"category": "report.released"},
        {"category": "re%"},
        {"target_id": "not-a-uuid"},
        {"since": "2026-03-10T00:00:00"},  # no offset: which day is meant?
        {"until": "yesterday"},
    ],
)
def test_a_malformed_request_is_refused(client, admin_session, params: dict) -> None:  # type: ignore[no-untyped-def, type-arg]
    _owner(client, admin_session, "bad")
    resp = client.get(URL, params=params)
    assert resp.status_code == 422, (params, resp.text)
    for value in params.values():
        if isinstance(value, str) and len(value) > 6:
            assert value not in resp.text  # the input is not echoed


def test_a_member_who_left_still_has_a_name_in_the_trail(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Removing a member does not rewrite what they did."""
    owner, tenant = _owner(client, admin_session, "left")
    clinician = switch_role(
        client,
        admin_session,
        email="left-clinician@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    client.post("/api/v1/patients", json={"display_name": "Synthetic Before Leaving"})
    login(client, owner.email)
    select_tenant(client, tenant.id)
    members = client.get("/api/v1/members").json()
    membership = next(m for m in members if m["user_id"] == str(clinician.id))
    assert client.delete(f"/api/v1/members/{membership['membership_id']}").status_code in (200, 204)

    created = next(i for i in _walk(client) if i["action"] == "patient.create")

    assert created["actor"]["user_id"] == str(clinician.id)
    assert created["actor"]["display_name"] == clinician.display_name
