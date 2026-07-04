"""Member administration: an owner lists the team, changes roles, and removes members.

Owner-only, tenant-scoped (memberships is non-RLS, so scoping is explicit), with guards: no
self-target, and the tenant must keep at least one owner. Audit carries role codes only.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.auth.authz import Action, can
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.models import Membership
from tests.helpers import login_as, provision_staff


def test_member_admin_authz_matrix() -> None:
    for action in (Action.MEMBER_LIST, Action.MEMBER_ROLE_CHANGE, Action.MEMBER_REMOVE):
        assert can(Role.OWNER, action) is True
        for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
            assert can(role, action) is False


def test_owner_lists_changes_and_removes(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="ma-owner@synthetic.example",
        tenant_name="MA Clinic",
        tenant_slug="ma-clinic",
        role=Role.OWNER,
    )
    # Add a second member (clinician) to this tenant.
    from tests.helpers import make_membership, make_user

    clin = make_user(admin_session, email="ma-clin@synthetic.example", name="MA Clinician")
    m = make_membership(admin_session, user_id=clin.id, tenant_id=tenant.id, role=Role.CLINICIAN)
    admin_session.commit()

    members = client.get("/api/v1/members").json()
    assert client.get("/api/v1/members").status_code == 200
    assert {mm["email"] for mm in members} == {
        "ma-owner@synthetic.example",
        "ma-clin@synthetic.example",
    }

    # Change the clinician to assistant.
    r = client.patch(f"/api/v1/members/{m.id}", json={"role": "assistant"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "assistant"

    # Remove them.
    assert client.delete(f"/api/v1/members/{m.id}").status_code == 200
    remaining = (
        admin_session.execute(select(Membership).where(Membership.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    assert len(remaining) == 1  # only the owner left


def test_non_owner_cannot_administer_members(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        slug = f"mma-{role.value}"[:60]
        login_as(
            client,
            admin_session,
            email=f"{role.value}@mma.example",
            tenant_name=slug,
            tenant_slug=slug,
            role=role,
        )
        assert client.get("/api/v1/members").status_code == 403
        assert (
            client.patch(f"/api/v1/members/{uuid.uuid4()}", json={"role": "assistant"}).status_code
            == 403
        )
        assert client.delete(f"/api/v1/members/{uuid.uuid4()}").status_code == 403


def test_cross_tenant_member_target_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Owner A; a member exists in tenant B. A cannot change or remove B's membership.
    _owner_a, _tenant_a = login_as(
        client,
        admin_session,
        email="ma-a@synthetic.example",
        tenant_name="MA A",
        tenant_slug="ma-a",
        role=Role.OWNER,
    )
    _user_b, tenant_b = provision_staff(
        admin_session,
        email="ma-b@synthetic.example",
        tenant_name="MA B",
        tenant_slug="ma-b",
        role=Role.CLINICIAN,
    )
    b_membership = admin_session.execute(
        select(Membership).where(Membership.tenant_id == tenant_b.id)
    ).scalar_one()
    assert (
        client.patch(f"/api/v1/members/{b_membership.id}", json={"role": "assistant"}).status_code
        == 404
    )
    assert client.delete(f"/api/v1/members/{b_membership.id}").status_code == 404


def test_owner_cannot_target_self(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="ma-self@synthetic.example",
        tenant_name="MA Self",
        tenant_slug="ma-self",
        role=Role.OWNER,
    )
    my = admin_session.execute(
        select(Membership).where(Membership.tenant_id == tenant.id)
    ).scalar_one()
    assert client.patch(f"/api/v1/members/{my.id}", json={"role": "clinician"}).status_code == 409
    assert client.delete(f"/api/v1/members/{my.id}").status_code == 409


def test_two_owners_can_demote_one(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # With two owners, demoting one is allowed (the other remains).
    _owner_a, tenant = login_as(
        client,
        admin_session,
        email="ma-o1@synthetic.example",
        tenant_name="MA Owners",
        tenant_slug="ma-owners",
        role=Role.OWNER,
    )
    from tests.helpers import make_membership, make_user

    owner_b = make_user(admin_session, email="ma-o2@synthetic.example", name="Owner Two")
    mb = make_membership(admin_session, user_id=owner_b.id, tenant_id=tenant.id, role=Role.OWNER)
    admin_session.commit()
    assert client.patch(f"/api/v1/members/{mb.id}", json={"role": "clinician"}).status_code == 200


def test_last_owner_guard_at_service_layer(admin_session) -> None:  # type: ignore[no-untyped-def]
    # The "keep >=1 owner" invariant is defense-in-depth: unreachable via the API (demoting an
    # owner requires ANOTHER acting owner, so >=2 owners exist), but enforced at the service so a
    # non-API caller cannot orphan a tenant. Exercise it directly with a non-self acting id.
    import pytest

    from hadp_api.errors import Conflict
    from hadp_api.modules.tenancy import service as tenancy_service
    from tests.helpers import make_membership, make_tenant, make_user

    tenant = make_tenant(admin_session, name="Last Owner", slug="last-owner")
    owner = make_user(admin_session, email="lo-owner@synthetic.example")
    m = make_membership(admin_session, user_id=owner.id, tenant_id=tenant.id, role=Role.OWNER)
    admin_session.commit()
    with pytest.raises(Conflict):
        tenancy_service.change_member_role(
            admin_session,
            tenant_id=tenant.id,
            membership_id=m.id,
            new_role=Role.CLINICIAN,
            acting_user_id=uuid.uuid4(),  # non-self, so we reach the last-owner check
        )
    admin_session.rollback()
    with pytest.raises(Conflict):
        tenancy_service.remove_member(
            admin_session,
            tenant_id=tenant.id,
            membership_id=m.id,
            acting_user_id=uuid.uuid4(),
        )
    admin_session.rollback()


def test_role_change_is_audited_with_roles_only(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="ma-aud@synthetic.example",
        tenant_name="MA Audit",
        tenant_slug="ma-audit",
        role=Role.OWNER,
    )
    from tests.helpers import make_membership, make_user

    u = make_user(admin_session, email="ma-aud-c@synthetic.example", name="Aud Clin")
    m = make_membership(admin_session, user_id=u.id, tenant_id=tenant.id, role=Role.CLINICIAN)
    admin_session.commit()
    client.patch(f"/api/v1/members/{m.id}", json={"role": "assistant"})
    event = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "member.role_changed")
    ).scalar_one()
    assert event.detail == {"old_role": "clinician", "new_role": "assistant"}
    assert "email" not in event.detail and "display_name" not in event.detail
