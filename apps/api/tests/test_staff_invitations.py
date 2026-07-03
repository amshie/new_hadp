"""Staff invitations: a clinic OWNER invites a colleague who self-onboards via a link.

The load-bearing properties (a staff member has broad, cross-patient access within their
clinic): every management endpoint is OWNER-only, every query is tenant-scoped, the invite
token is single-use and cannot be replayed cross-tenant, and the redeemer receives the ROLE
the owner fixed — never one of their own choosing.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from hadp_api.auth.authz import Action, can
from hadp_api.main import app
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import InvitationStatus, Role
from hadp_api.modules.identity.models import User
from hadp_api.modules.staff_invitations.models import StaffInvitation
from hadp_api.modules.tenancy.models import Membership
from tests.helpers import login, login_as, make_user


def test_staff_invite_authz_matrix() -> None:
    """Pure-Python matrix: STAFF_INVITE_CREATE is OWNER-only (no DB needed)."""
    assert can(Role.OWNER, Action.STAFF_INVITE_CREATE) is True
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        assert can(role, Action.STAFF_INVITE_CREATE) is False


def test_owner_invites_and_colleague_self_onboards(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner@synthetic.example",
        tenant_name="Invite Clinic",
        tenant_slug="invite-clinic",
        role=Role.OWNER,
    )
    created = client.post("/api/v1/staff-invitations", json={"role": "clinician"})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "clinician"
    assert body["status"] == "pending"
    assert "/team-einladung?tenant=" in body["invitation_url"]
    token = body["invitation_token"]

    # Colleague redeems on a fresh client (no staff session).
    with TestClient(app) as anon:
        redeemed = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "New Clinician",
                "email": "newclin@synthetic.example",
            },
        )
        assert redeemed.status_code == 200, redeemed.text
        assert redeemed.json()["role"] == "clinician"

    # The new user can now log in and is a clinician of exactly this tenant.
    with TestClient(app) as newc:
        login(newc, "newclin@synthetic.example")
        tenants = newc.get("/api/v1/tenancy/my-tenants").json()
        assert len(tenants) == 1
        assert tenants[0]["tenant_id"] == str(tenant.id)
        assert tenants[0]["role"] == "clinician"

    # Invitation consumed; the created user is synthetic + active.
    inv = admin_session.execute(select(StaffInvitation)).scalar_one()
    assert inv.status == InvitationStatus.REDEEMED
    assert inv.redeemed_user_id is not None
    user = admin_session.get(User, inv.redeemed_user_id)
    assert user is not None and user.is_synthetic is True and user.is_active is True


def test_non_owner_cannot_manage_staff_invites(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        slug = f"noown-{role.value}"[:60]
        login_as(
            client,
            admin_session,
            email=f"{role.value}@noown.example",
            tenant_name=slug,
            tenant_slug=slug,
            role=role,
        )
        assert (
            client.post("/api/v1/staff-invitations", json={"role": "clinician"}).status_code == 403
        )
        assert client.get("/api/v1/staff-invitations").status_code == 403
        assert client.post(f"/api/v1/staff-invitations/{uuid.uuid4()}/revoke").status_code == 403


def test_redeemer_cannot_choose_their_own_role(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner2@synthetic.example",
        tenant_name="Role Clinic",
        tenant_slug="role-clinic",
        role=Role.OWNER,
    )
    token = client.post("/api/v1/staff-invitations", json={"role": "assistant"}).json()[
        "invitation_token"
    ]
    with TestClient(app) as anon:
        # Malicious redeemer smuggles role=owner — the extra field is ignored; the invite's
        # role (assistant) is applied.
        redeemed = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "Sneaky",
                "email": "sneaky@synthetic.example",
                "role": "owner",
            },
        )
        assert redeemed.status_code == 200, redeemed.text
        assert redeemed.json()["role"] == "assistant"
    membership = admin_session.execute(
        select(Membership)
        .join(User, User.id == Membership.user_id)
        .where(User.email == "sneaky@synthetic.example")
    ).scalar_one()
    assert membership.role == Role.ASSISTANT


def test_redeem_is_single_use(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner3@synthetic.example",
        tenant_name="Single Clinic",
        tenant_slug="single-clinic",
        role=Role.OWNER,
    )
    token = client.post("/api/v1/staff-invitations", json={"role": "clinician"}).json()[
        "invitation_token"
    ]
    with TestClient(app) as anon:
        first = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "First",
                "email": "first@synthetic.example",
            },
        )
        assert first.status_code == 200, first.text
        # Replaying the same token is a neutral 404 (single-use).
        second = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "Second",
                "email": "second@synthetic.example",
            },
        )
        assert second.status_code == 404
    # The replay created NO second user.
    assert (
        admin_session.execute(
            select(User).where(User.email == "second@synthetic.example")
        ).scalar_one_or_none()
        is None
    )


def test_cross_tenant_token_replay_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A's valid token presented under B's tenant reveals nothing and creates nothing."""
    _owner, tenant_a = login_as(
        client,
        admin_session,
        email="owner-a@synthetic.example",
        tenant_name="Clinic SA",
        tenant_slug="clinic-sa",
        role=Role.OWNER,
    )
    token = client.post("/api/v1/staff-invitations", json={"role": "clinician"}).json()[
        "invitation_token"
    ]
    from tests.helpers import make_tenant

    tenant_b = make_tenant(admin_session, name="Clinic SB", slug="clinic-sb")
    admin_session.commit()

    with TestClient(app) as anon:
        replay = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant_b.id),
                "token": token,
                "display_name": "Cross",
                "email": "cross@synthetic.example",
            },
        )
        assert replay.status_code == 404
    # No user or membership was created under either tenant.
    assert (
        admin_session.execute(
            select(User).where(User.email == "cross@synthetic.example")
        ).scalar_one_or_none()
        is None
    )
    # The A invitation is still pending (untouched by the cross-tenant attempt).
    inv = admin_session.execute(
        select(StaffInvitation).where(StaffInvitation.tenant_id == tenant_a.id)
    ).scalar_one()
    assert inv.status == InvitationStatus.PENDING


def test_owner_cannot_revoke_other_tenant_invitation(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner_a, _tenant_a = login_as(
        client,
        admin_session,
        email="rowner-a@synthetic.example",
        tenant_name="Revoke A",
        tenant_slug="revoke-a",
        role=Role.OWNER,
    )
    invitation_id = client.post("/api/v1/staff-invitations", json={"role": "clinician"}).json()[
        "invitation_id"
    ]
    # A different owner in a different tenant cannot revoke A's invitation → 404 (no leak).
    with TestClient(app) as owner_b:
        from tests.helpers import provision_staff

        provision_staff(
            admin_session,
            email="rowner-b@synthetic.example",
            tenant_name="Revoke B",
            tenant_slug="revoke-b",
            role=Role.OWNER,
        )
        login(owner_b, "rowner-b@synthetic.example")
        tenants = owner_b.get("/api/v1/tenancy/my-tenants").json()
        owner_b.post("/api/v1/tenancy/select-tenant", json={"tenant_id": tenants[0]["tenant_id"]})
        assert owner_b.post(f"/api/v1/staff-invitations/{invitation_id}/revoke").status_code == 404
    # A's invitation is still pending.
    inv = admin_session.execute(select(StaffInvitation)).scalar_one()
    assert inv.status == InvitationStatus.PENDING


def test_revoked_invitation_cannot_be_redeemed(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner4@synthetic.example",
        tenant_name="Revoke Clinic",
        tenant_slug="revoke-clinic",
        role=Role.OWNER,
    )
    created = client.post("/api/v1/staff-invitations", json={"role": "clinician"}).json()
    assert (
        client.post(f"/api/v1/staff-invitations/{created['invitation_id']}/revoke").status_code
        == 200
    )
    with TestClient(app) as anon:
        redeemed = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": created["invitation_token"],
                "display_name": "TooLate",
                "email": "toolate@synthetic.example",
            },
        )
        assert redeemed.status_code == 404


def test_redeem_with_existing_email_is_neutral_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # A taken email is indistinguishable from every other non-redeemable state (no oracle that
    # would let a token holder probe which emails are registered).
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner5@synthetic.example",
        tenant_name="Conflict Clinic",
        tenant_slug="conflict-clinic",
        role=Role.OWNER,
    )
    make_user(admin_session, email="taken@synthetic.example")
    admin_session.commit()
    token = client.post("/api/v1/staff-invitations", json={"role": "clinician"}).json()[
        "invitation_token"
    ]
    with TestClient(app) as anon:
        redeemed = anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "Dup",
                "email": "taken@synthetic.example",
            },
        )
        assert redeemed.status_code == 404, redeemed.text
    # The invitation is NOT consumed (the colleague can retry with a different email).
    inv = admin_session.execute(select(StaffInvitation)).scalar_one()
    assert inv.status == InvitationStatus.PENDING


def test_redeem_is_audited_with_role_only(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="owner6@synthetic.example",
        tenant_name="Audit Clinic",
        tenant_slug="audit-clinic",
        role=Role.OWNER,
    )
    token = client.post("/api/v1/staff-invitations", json={"role": "assistant"}).json()[
        "invitation_token"
    ]
    with TestClient(app) as anon:
        anon.post(
            "/api/v1/staff-invitations/redeem",
            json={
                "tenant": str(tenant.id),
                "token": token,
                "display_name": "Audited Person",
                "email": "audited@synthetic.example",
            },
        )
    event = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "staff_invite.redeemed")
    ).scalar_one()
    assert event.detail == {"role": "assistant"}
    # No PII in the audit detail.
    assert "email" not in event.detail and "display_name" not in event.detail
