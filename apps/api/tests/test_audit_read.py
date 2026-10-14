"""The clinic reads its own audit trail (go-live plan A9).

OWNER only; exactly the events recorded for that clinic — never another clinic's, and never
the tenant-less events (sign-ins, denials before a clinic is selected) that row-level security
would let through; newest first, paged by an opaque cursor that neither repeats nor drops an
event at a page boundary; filtered by a closed set of categories, by actor, target and time;
and the read is itself recorded.
"""

from __future__ import annotations

import ast
import base64
import re
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text

from hadp_api.config import get_settings
from hadp_api.modules.audit import service as audit_service
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import AuditCategory, Role
from tests.helpers import (
    login,
    login_as,
    make_membership,
    provision_staff,
    select_tenant,
    switch_role,
)

URL = "/api/v1/audit-events"
_API_SRC = Path(__file__).resolve().parents[1] / "src" / "hadp_api"
_WEB_SRC = Path(__file__).resolve().parents[2] / "web" / "src"
_AUDIT_COPY = _WEB_SRC / "lib" / "auditCopy.ts"
# The audit page's wording, German and English (ADR-0007).
_MESSAGES = _WEB_SRC / "lib" / "i18n" / "messages"


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


def _tenant_event_ids(admin_session, tenant_id) -> set[str]:  # type: ignore[no-untyped-def]
    rows = admin_session.execute(select(AuditEvent.id).where(AuditEvent.tenant_id == tenant_id))
    return {str(i) for i in rows.scalars()}


def test_an_owner_reads_the_clinics_own_trail_newest_first(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _owner(client, admin_session, "own")
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic Audit"}).json()["id"]

    body = client.get(URL).json()

    actions = [i["action"] for i in body["items"]]
    assert actions[0] == "patient.create"
    created = body["items"][0]
    assert (created["target_type"], created["target_id"]) == ("patient", pid)
    # Who acted: the account's name and e-mail — a colleague in the reader's own clinic.
    assert created["actor"] == {
        "user_id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
    }
    # The detail is returned as it was written; the time in UTC.
    entered = next(i for i in body["items"] if i["action"] == "tenant.select")
    assert entered["detail"] == {"role": "owner"}
    assert entered["occurred_at"].endswith(("Z", "+00:00"))
    # The request's correlation id is the operator's handle, not part of what a clinic reads.
    assert set(created) == {
        "id",
        "occurred_at",
        "action",
        "actor",
        "target_type",
        "target_id",
        "detail",
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
    # Which filters were set. Of their values only the category — one of a closed set.
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
    # The next read shows it — and "who read this trail" is a question the trail answers.
    assert client.get(URL).json()["items"][0]["action"] == "audit.read"
    reads = _walk(client, category="audit")
    assert reads and {i["action"] for i in reads} == {"audit.read"}
    assert all(i["actor"]["user_id"] == str(user.id) for i in reads)
    # Asking for that family without reads is asking for nothing.
    assert _walk(client, category="audit", exclude_reads="true") == []


def test_reading_is_throttled_per_account_and_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Every read writes an event into a clinic's trail, and nothing is removed from it. The
    limit bounds what one account's reading adds to one clinic — a colleague, and the same
    person in another clinic, are not held up by it."""
    owner, tenant = _owner(client, admin_session, "throttle")
    for _ in range(120):
        assert client.get(URL, params={"limit": 1}).status_code == 200

    refused = client.get(URL, params={"limit": 1})

    assert refused.status_code == 429
    events = admin_session.execute(select(AuditEvent)).scalars().all()
    assert sum(1 for e in events if e.action == "audit.read" and e.tenant_id == tenant.id) == 120
    # The refusal leaves a trace too — without tenant or actor: it says that a read was
    # throttled, not whose. One event per window in which reads were refused.
    throttled = [e for e in events if e.action == "rate_limited"]
    assert [(e.tenant_id, e.actor_user_id, e.detail) for e in throttled] == [
        (None, None, {"action": "audit.read"})
    ]

    # The same person in another clinic reads that clinic's trail.
    _other_owner, elsewhere = provision_staff(
        admin_session,
        email="owner-throttle-elsewhere@synthetic.example",
        tenant_name="Audit Throttle Elsewhere",
        tenant_slug="audit-throttle-elsewhere",
        role=Role.OWNER,
    )
    make_membership(admin_session, user_id=owner.id, tenant_id=elsewhere.id, role=Role.OWNER)
    admin_session.commit()
    select_tenant(client, elsewhere.id)
    assert client.get(URL, params={"limit": 1}).status_code == 200
    # And a second owner of the first clinic reads it.
    switch_role(
        client,
        admin_session,
        email="second-owner-throttle@synthetic.example",
        tenant=tenant,
        role=Role.OWNER,
    )
    assert client.get(URL, params={"limit": 1}).status_code == 200


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
    other_user, other = _owner(client, admin_session, "other")
    other_patient = client.post(
        "/api/v1/patients", json={"display_name": "Synthetic Other Clinic"}
    ).json()["id"]
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
    # Asking for the other clinic by a filter — its record, its member, its family of events —
    # returns nothing, and nothing but this clinic's own events however the question is put.
    mine = _tenant_event_ids(admin_session, tenant.id)
    assert _walk(client, target_id=other_patient) == []
    assert _walk(client, actor_user_id=str(other_user.id)) == []
    assert _walk(client, category="report") == []
    assert _walk(client, category="patient") == []
    # A position taken from the other clinic's trail is a position in time, nothing more.
    forged = audit_service._encode_cursor(foreign)
    from_there = _walk(client, cursor=forged)
    assert {i["id"] for i in from_there} <= mine
    assert {i["id"] for i in _walk(client)} <= _tenant_event_ids(admin_session, tenant.id)


def test_the_tenant_filter_alone_isolates_a_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The explicit tenant filter is the control. Proven on a session that bypasses row-level
    security, where nothing else could keep another clinic's or a tenant-less event out."""
    _mine_user, mine = provision_staff(
        admin_session,
        email="bypass-mine@synthetic.example",
        tenant_name="Audit Bypass Mine",
        tenant_slug="audit-bypass-mine",
        role=Role.OWNER,
    )
    _other_user, other = provision_staff(
        admin_session,
        email="bypass-other@synthetic.example",
        tenant_name="Audit Bypass Other",
        tenant_slug="audit-bypass-other",
        role=Role.OWNER,
    )
    own = _event(admin_session, mine.id, "report.released")
    foreign = _event(admin_session, other.id, "report.released")
    tenantless = _event(admin_session, None, "login.failed")
    admin_session.commit()

    page = audit_service.list_tenant_events(admin_session, tenant_id=mine.id, limit=200)

    ids = {e.id for e in page.events}
    assert own.id in ids
    assert foreign.id not in ids
    assert tenantless.id not in ids
    assert {e.tenant_id for e in page.events} == {mine.id}


def test_a_colleague_who_also_works_elsewhere_shows_only_what_they_did_here(  # type: ignore[no-untyped-def]
    client, admin_session
) -> None:
    person, here = _owner(client, admin_session, "multi-here")
    _elsewhere_owner, elsewhere = provision_staff(
        admin_session,
        email="owner-multi-elsewhere@synthetic.example",
        tenant_name="Audit Multi Elsewhere",
        tenant_slug="audit-multi-elsewhere",
        role=Role.OWNER,
    )
    make_membership(admin_session, user_id=person.id, tenant_id=elsewhere.id, role=Role.CLINICIAN)
    admin_session.commit()
    select_tenant(client, elsewhere.id)
    made = client.post("/api/v1/patients", json={"display_name": "Synthetic Elsewhere"})
    assert made.status_code == 201, made.text
    select_tenant(client, here.id)

    items = _walk(client, actor_user_id=str(person.id))

    assert items
    assert {i["id"] for i in items} <= _tenant_event_ids(admin_session, here.id)
    assert "patient.create" not in {i["action"] for i in items}
    assert _walk(client, target_id=made.json()["id"]) == []


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
    """Events as the routes write them: a read of a record is filed under the record; a report,
    under the report."""
    user, tenant = _owner(client, admin_session, "filters")
    patient, report, item = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    colleague = uuid.uuid4()
    day = datetime(2026, 3, 10, 9, tzinfo=UTC)
    rows = [
        ("patient.read", "patient", patient, user.id, day),
        ("patient.create", "patient", patient, user.id, day + timedelta(hours=1)),
        ("patient.list", None, None, user.id, day + timedelta(hours=2)),
        ("observation.read", "patient", patient, user.id, day + timedelta(hours=3)),
        ("review_item.resolved", "review_item", item, user.id, day + timedelta(hours=4)),
        # Only a wildcard would take this for the "review_item" family …
        ("reviewXitem.resolved", "review_item", item, user.id, day + timedelta(hours=5)),
        # … and only a prefix without its dot would take this one.
        ("review_items.resolved", "review_item", item, user.id, day + timedelta(hours=6)),
        ("report.released", "report", report, user.id, day + timedelta(days=1)),
        ("report.patient_view", "report", report, None, day + timedelta(days=2)),
    ]
    for action, target_type, target, actor, at in rows:
        _event(
            admin_session,
            tenant.id,
            action,
            target_id=target,
            target_type=target_type,
            actor_user_id=actor,
            created_at=at,
        )
    admin_session.commit()
    window = {"since": "2026-03-01T00:00:00Z", "until": "2026-04-01T00:00:00Z"}

    def actions(**params: object) -> list[str]:
        return sorted(i["action"] for i in _walk(client, **{**window, **params}))

    # A category is the part before the first dot.
    assert actions(category="patient") == ["patient.create", "patient.list", "patient.read"]
    assert actions(category="observation") == ["observation.read"]
    assert actions(category="report") == ["report.patient_view", "report.released"]
    # "_" is a letter here, not a wildcard.
    assert actions(category="review_item") == ["review_item.resolved"]
    # Staff reads and listings can be left out; a report opened through a patient link is not
    # one of them.
    assert actions(exclude_reads="true") == [
        "patient.create",
        "report.patient_view",
        "report.released",
        "reviewXitem.resolved",
        "review_item.resolved",
        "review_items.resolved",
    ]
    # By record: what is filed under that record — its reads included, the report not.
    assert actions(target_id=str(patient)) == ["observation.read", "patient.create", "patient.read"]
    assert actions(target_id=str(report)) == ["report.patient_view", "report.released"]
    assert len(actions(actor_user_id=str(user.id))) == 8
    assert actions(actor_user_id=str(colleague)) == []
    # since is inclusive, until exclusive — to the instant.
    first = day.isoformat()
    assert "patient.read" in actions(since=first)
    assert "patient.read" not in actions(since=(day + timedelta(microseconds=1)).isoformat())
    assert "patient.read" not in actions(until=first)
    assert "patient.read" in actions(until=(day + timedelta(microseconds=1)).isoformat())
    # An event nobody signed in caused has no actor.
    opened = next(i for i in _walk(client, **window) if i["action"] == "report.patient_view")
    assert opened["actor"] is None


def test_a_time_is_given_in_utc_whatever_zone_the_database_session_reports(  # type: ignore[no-untyped-def]
    client, admin_session, monkeypatch
) -> None:
    """The driver hands back a timestamp in the session's zone. The answer names one instant
    and writes it one way."""
    _owner(client, admin_session, "zone")
    berlin = timezone(timedelta(hours=2))
    event = AuditEvent(
        id=uuid.uuid4(),
        action="tenant.select",
        detail={},
        created_at=datetime(2026, 10, 12, 18, 59, 30, tzinfo=berlin),
    )
    monkeypatch.setattr(
        audit_service,
        "list_tenant_events",
        lambda *_args, **_kwargs: audit_service.AuditPage(events=[event], next_cursor=None),
    )

    (item,) = client.get(URL).json()["items"]

    assert item["occurred_at"] in ("2026-10-12T16:59:30Z", "2026-10-12T16:59:30+00:00")


def _cursor(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


@pytest.mark.parametrize(
    "params",
    [
        {"cursor": "not-a-cursor"},
        {"cursor": _cursor("2026-01-01T12:00:00+00:00|not-a-uuid")},
        # No offset: a position in which zone?
        {"cursor": _cursor("2026-01-01T12:00:00|3f0b2c1e-7a55-4c0e-9d53-0a4f6f0d2b11")},
        {"limit": 0},
        {"limit": 201},
        # A category is one of a closed set — not a pattern, and not a place to put text.
        {"category": "Report"},
        {"category": "report.released"},
        {"category": "re%"},
        {"category": "patien_"},
        {"category": "rate_limited"},
        {"category": "auth"},
        {"category": "erika_mustermann_diabetes"},
        {"target_id": "not-a-uuid"},
        {"since": "2026-03-10T00:00:00"},  # no offset: which day is meant?
        {"until": "2026-03-10T00:00:00"},
        {"until": "yesterday"},
    ],
)
def test_a_malformed_request_is_refused(client, admin_session, params: dict) -> None:  # type: ignore[no-untyped-def, type-arg]
    _user, tenant = _owner(client, admin_session, "bad")
    resp = client.get(URL, params=params)
    assert resp.status_code == 422, (params, resp.text)
    for value in params.values():
        if isinstance(value, str) and len(value) > 6:
            assert value not in resp.text  # the input is not echoed
    # A refused read is not a read: nothing was returned, nothing is recorded as read — and
    # nothing of the request reached the trail.
    recorded = admin_session.execute(
        select(AuditEvent.action).where(AuditEvent.tenant_id == tenant.id)
    ).scalars()
    assert set(recorded) == {"tenant.select"}


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

    assert created["actor"] == {
        "user_id": str(clinician.id),
        "display_name": clinician.display_name,
        "email": clinician.email,
    }


# --- The vocabulary of the trail, held against the code that writes it ---------------------


def _audit_writes() -> list[tuple[str, bool, str | None, str]]:
    """Every audit write in the API source: (action, recorded with a tenant, target type, where)."""
    writes: list[tuple[str, bool, str | None, str]] = []
    unresolved: list[str] = []
    for path in sorted(_API_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text())
        constants = {
            target.id: node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in {"record_audit", "record_security_event"}:
                continue
            where = f"{path.relative_to(_API_SRC)}:{node.lineno}"
            keywords = {k.arg: k.value for k in node.keywords if k.arg}
            action = keywords.get("action")
            if isinstance(action, ast.Constant) and isinstance(action.value, str):
                code = action.value
            elif isinstance(action, ast.Name) and action.id in constants:
                code = constants[action.id]
            else:
                unresolved.append(where)
                continue
            tenant = keywords.get("tenant_id")
            with_tenant = tenant is not None and not (
                isinstance(tenant, ast.Constant) and tenant.value is None
            )
            target = keywords.get("target_type")
            target_type = target.value if isinstance(target, ast.Constant) else None
            assert target is None or target_type, f"{where}: target type is not a literal"
            writes.append((code, with_tenant, target_type, where))
    # The one write whose action is not a literal: record_security_event passing its own on.
    assert [w.split(":")[0] for w in unresolved] == ["modules/audit/service.py"], unresolved
    return writes


def _copy_keys(name: str) -> set[str]:
    """The keys of one `const NAME… = { … };` table in the web's audit copy."""
    source = _AUDIT_COPY.read_text()
    block = re.search(rf"const {name}\b[^=]*= \{{\n(.*?)\n\}};", source, re.DOTALL)
    assert block, name
    return set(re.findall(r'^  "?([A-Za-z_.]+)"?:', block.group(1), re.MULTILINE))


def test_the_categories_are_the_families_of_events_a_clinic_can_hold() -> None:
    writes = _audit_writes()
    with_tenant = {action for action, tenant, _target, _where in writes if tenant}
    # The category filter is "<family>." — it relies on every such action having a dot.
    assert all("." in action for action in with_tenant)
    families = {action.split(".")[0] for action in with_tenant}

    assert families == {c.value for c in AuditCategory}
    # What is recorded without a tenant, and so never in any clinic's trail. The page that shows
    # the trail says so; a new family here needs that sentence looked at.
    tenantless = {action for action, tenant, _target, _where in writes if not tenant}
    assert tenantless == {
        "auth.dev_login",
        "auth.logout",
        "login.failed",
        "csrf.denied",
        "rate_limited",
        "authz.denied",  # before a clinic is selected, or by someone who is no longer a member
    }


def test_the_web_names_exactly_what_the_trail_can_hold() -> None:
    """A label for an action that is never written is a claim about a trail that does not
    exist; an action without a label is shown as a bare code."""
    writes = _audit_writes()
    assert _copy_keys("ACTION_LABELS") == {action for action, tenant, _t, _w in writes if tenant}
    assert _copy_keys("TARGET_LABELS") == {target for _a, _tenant, target, _w in writes if target}
    assert _copy_keys("CATEGORY_LABELS") == {c.value for c in AuditCategory}
    # What the page says a search by patient record finds (auditPage.notShown.byRecord in the
    # web's messages): the events filed under the record itself.
    assert {action for action, _tenant, target, _w in writes if target == "patient"} == {
        "patient.create",
        "patient.read",
        "observation.read",
        "interpretation.read",
        "consent.read",
        "consent.granted",
        "consent.withdrawn",
        "document.list",
        "privacy.export",
    }


def test_audit_events_are_written_in_one_way_only() -> None:
    """The tests in this section read the source for calls of `record_audit` and
    `record_security_event`, and for route decorators. They see nothing else — so nothing else
    may write an event or register a route: no audit function under another name, no
    `AuditEvent(...)` built outside the audit module, no route added by a call."""
    for path in sorted(_API_SRC.rglob("*.py")):
        where = str(path.relative_to(_API_SRC))
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom | ast.Import):
                renamed = [
                    alias.name
                    for alias in node.names
                    if alias.asname and alias.name in {"record_audit", "record_security_event"}
                ]
                assert not renamed, f"{where}:{node.lineno} imports {renamed} under another name"
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name | ast.Attribute):
                bound = getattr(node.value, "id", None) or getattr(node.value, "attr", None)
                assert bound not in {
                    "record_audit",
                    "record_security_event",
                }, f"{where}:{node.lineno} binds {bound} to another name"
            if not isinstance(node, ast.Call):
                continue
            called = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if called == "AuditEvent":
                assert where == "modules/audit/service.py", f"{where}:{node.lineno} builds an event"
            assert called not in {
                "add_api_route",
                "add_route",
                "api_route",
            }, f"{where}:{node.lineno} registers a route by a call"


# A GET handler that records nothing -> the words by which the page names that read as not
# recorded, in German and in English. None: no clinic's data (liveness; the session's own
# identity and clinics; the KPI catalog and the role matrix, reference data the same for every
# clinic).
SILENT_READS: dict[tuple[str, str], tuple[str, str] | None] = {
    ("health.py", "health"): None,
    ("auth_routes.py", "me"): None,
    ("tenancy_routes.py", "my_tenants"): None,
    ("kpi_routes.py", "core_catalog"): None,
    ("members_routes.py", "list_role_permissions"): None,
    ("reports_routes.py", "get_report"): ("das Lesen eines Berichts", "a report read by staff"),
    ("members_routes.py", "list_members"): ("Mitglieder", "members"),
    ("staff_invitations_routes.py", "list_staff_invitations"): (
        "Teameinladungen",
        "team invitations",
    ),
    ("privacy_routes.py", "list_deletion_requests"): ("Löschanträge", "deletion requests"),
    ("privacy_routes.py", "list_patient_data_exports"): (
        "Verlauf der Datenauskünfte",
        "history of data exports",
    ),
}

# The sentence that lists them, in each language: its file, how it opens, the word that joins
# the last two, and every read it names.
_NOT_RECORDED = (
    (
        "de.ts",
        "Derzeit nicht protokolliert:",
        " und ",
        {
            "das Lesen eines Berichts durch Mitarbeitende",
            "das Lesen der Verwaltungslisten",
            "Mitglieder",
            "Teameinladungen",
            "Löschanträge",
            "Verlauf der Datenauskünfte",
        },
    ),
    (
        "en.ts",
        "Not recorded at present:",
        " and ",
        {
            "a report read by staff",
            "the reading of the administrative lists",
            "members",
            "team invitations",
            "deletion requests",
            "history of data exports",
        },
    ),
)


def test_the_reads_that_leave_no_trace_are_the_ones_the_page_names() -> None:
    """The page lists what is not recorded. A read that starts or stops being recorded changes
    that list (auditPage.notShown.notRecorded, in both languages) — this fails until the table
    above and the sentence in each language say what the code does."""
    silent: set[tuple[str, str]] = set()
    for path in sorted((_API_SRC / "api").glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            is_get = any(
                isinstance(d, ast.Call) and getattr(d.func, "attr", None) == "get"
                for d in node.decorator_list
            )
            records = any(
                isinstance(call, ast.Call)
                and (getattr(call.func, "id", None) or getattr(call.func, "attr", None))
                == "record_audit"
                for call in ast.walk(node)
            )
            if is_get and not records:
                silent.add((path.name, node.name))

    assert silent == set(SILENT_READS)
    for language, (file, opening, conjunction, expected) in enumerate(_NOT_RECORDED):
        source = " ".join((_MESSAGES / file).read_text().split())
        sentence = re.search(rf'{re.escape(opening)}([^"]*)"', source)
        assert sentence, f"{file} no longer says what is not recorded"
        named = sentence.group(1)
        for handler, words in SILENT_READS.items():
            if words is not None:
                assert words[language] in named, f"{file} does not name {handler} as not recorded"
        # Nothing else is claimed to be unrecorded: every listed read is one of the above.
        pieces = re.split(rf",|\(|\)|{conjunction}", named)
        assert {w.strip(" .") for w in pieces if w.strip(" .")} == expected, file
