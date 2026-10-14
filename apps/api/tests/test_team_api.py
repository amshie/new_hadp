"""Team & Rollen (docs/notes/0016, part 2): an invitation's label and creator, each member's
latest activity, and the authorization matrix as the page that assigns roles reads it.

The label is the owner's note of whom a link is for: stored, listed to owners, never sent and
never in an audit event. Latest activity is the date of a member's latest event in this
clinic's trail. The matrix is `auth/authz.py` itself; the web's lines of "what a role may do"
(`apps/web/src/lib/roleCapabilities.ts`) are held against it here.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from hadp_api.auth.authz import Action, permissions_by_role
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.staff_invitations.models import StaffInvitation
from tests.helpers import (
    login,
    login_as,
    make_membership,
    make_user,
    select_tenant,
    switch_role,
)

_CAPABILITIES = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "roleCapabilities.ts"


def _owner(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"team-{slug}@synthetic.example",
        tenant_name=f"Team {slug}",
        tenant_slug=f"team-{slug}",
        role=Role.OWNER,
    )


def test_an_invitation_keeps_its_label_and_names_its_creator(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, _tenant = _owner(client, admin_session, "label")
    created = client.post(
        "/api/v1/staff-invitations",
        json={"role": "clinician", "label": "  s.johnson@clinic.example  "},
    )
    assert created.status_code == 201, created.text
    plain = client.post("/api/v1/staff-invitations", json={"role": "assistant", "label": "  "})
    assert plain.status_code == 201, plain.text

    listed = {i["invitation_id"]: i for i in client.get("/api/v1/staff-invitations").json()}
    labelled = listed[created.json()["invitation_id"]]
    assert labelled["label"] == "s.johnson@clinic.example"
    assert labelled["created_by"] == {
        "user_id": str(owner.id),
        "display_name": owner.display_name,
    }
    # A blank label is no label.
    assert listed[plain.json()["invitation_id"]]["label"] is None

    # Never in the trail: the event records the role and the status only.
    event = admin_session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "staff_invite.create",
            AuditEvent.target_id == uuid.UUID(labelled["invitation_id"]),
        )
    ).scalar_one()
    assert "johnson" not in str(event.detail)
    assert set(event.detail) == {"role", "status"}


def test_a_label_is_bounded(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "bounded")
    resp = client.post("/api/v1/staff-invitations", json={"role": "clinician", "label": "x" * 201})
    assert resp.status_code == 422
    assert "x" * 50 not in resp.text
    made = admin_session.execute(
        select(StaffInvitation).where(StaffInvitation.tenant_id == tenant.id)
    ).first()
    assert made is None


def test_members_say_when_each_last_acted_in_this_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, tenant = _owner(client, admin_session, "active")
    # A colleague who has never signed in to this clinic.
    quiet = make_user(admin_session, email="team-quiet@synthetic.example", name="Quiet")
    make_membership(admin_session, user_id=quiet.id, tenant_id=tenant.id, role=Role.ASSISTANT)
    admin_session.commit()
    # A colleague who has: their selecting the clinic is their latest event.
    active = switch_role(
        client,
        admin_session,
        email="team-colleague@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    # The same colleague's events in another clinic do not count here.
    _, other = _owner(client, admin_session, "active-other")
    make_membership(admin_session, user_id=active.id, tenant_id=other.id, role=Role.CLINICIAN)
    admin_session.commit()

    login(client, owner.email)
    select_tenant(client, tenant.id)

    members = {m["email"]: m for m in client.get("/api/v1/members").json()}
    assert members["team-quiet@synthetic.example"]["last_active_at"] is None
    last = datetime.fromisoformat(members["team-colleague@synthetic.example"]["last_active_at"])
    assert last.tzinfo is not None
    latest_here = (
        admin_session.execute(
            select(AuditEvent.created_at)
            .where(AuditEvent.actor_user_id == active.id, AuditEvent.tenant_id == tenant.id)
            .order_by(AuditEvent.created_at.desc())
        )
        .scalars()
        .first()
    )
    assert last == latest_here
    assert members[owner.email]["last_active_at"] is not None


def test_the_role_matrix_is_the_authorization_matrix(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "matrix")
    resp = client.get("/api/v1/roles")
    assert resp.status_code == 200, resp.text
    body = {r["role"]: r["actions"] for r in resp.json()}
    assert body == {role.value: actions for role, actions in permissions_by_role().items()}
    # The two-tier gate, as the page will show it.
    assert "report.release" in body["medical_director"]
    assert "report.approve" not in body["medical_director"]
    assert "report.approve" in body["clinician"]
    assert "report.release" not in body["clinician"]


def test_the_role_matrix_is_for_the_owner(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="team-matrix-c@synthetic.example",
        tenant_name="Team Matrix C",
        tenant_slug="team-matrix-c",
        role=Role.CLINICIAN,
    )
    assert client.get("/api/v1/roles").status_code == 403


def test_the_web_names_every_action_once_and_each_line_is_whole() -> None:
    """Each line of "what a role may do" is a group of actions that the same roles hold; every
    action is in exactly one line. A new action, or a change that splits a line, fails here
    until the page's lines say what the matrix does."""
    source = _CAPABILITIES.read_text()
    block = re.search(r"export const CAPABILITIES = \[(.*?)\] as const;", source, re.S)
    assert block, "roleCapabilities.ts has no CAPABILITIES table"
    lines = re.findall(r'key: "(\w+)",\s*actions: \[(.*?)\]', block.group(1), re.S)
    assert lines
    named: list[str] = []
    grants = permissions_by_role()
    for key, actions_text in lines:
        actions = re.findall(r'"([a-z_]+\.[a-z_]+)"', actions_text)
        assert actions, key
        named.extend(actions)
        holders = [frozenset(r for r, a in grants.items() if action in a) for action in actions]
        assert len(set(holders)) == 1, f"the line {key!r} is held by different roles"
    assert sorted(named) == sorted(a.value for a in Action)
