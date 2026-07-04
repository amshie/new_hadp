"""Tenancy application service.

Member administration note: `memberships` is a NON-RLS table (it is read before tenant
selection), so every member-admin query below scopes by tenant_id EXPLICITLY — RLS will not
do it here. Cross-tenant targets resolve to the same NotFound as unknown ids (no leak).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.enums import Role
from hadp_api.modules.identity.models import User
from hadp_api.modules.tenancy.models import Membership, Tenant


@dataclass
class TenantMembership:
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    is_synthetic: bool
    role: Role


def list_memberships(db: Session, user_id: uuid.UUID) -> list[TenantMembership]:
    """Tenants the user may access (not RLS-protected; queried before tenant selection)."""
    rows = db.execute(
        select(Membership, Tenant)
        .join(Tenant, Tenant.id == Membership.tenant_id)
        .where(Membership.user_id == user_id)
        .order_by(Tenant.name)
    ).all()
    return [
        TenantMembership(
            tenant_id=t.id,
            tenant_name=t.name,
            tenant_slug=t.slug,
            is_synthetic=t.is_synthetic,
            role=m.role,
        )
        for (m, t) in rows
    ]


def get_membership(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Membership | None:
    return db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.tenant_id == tenant_id)
    ).scalar_one_or_none()


# --- Member administration (owner-only at the route layer) -------------------------------


@dataclass
class TenantMember:
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: Role
    member_since: str  # ISO timestamp of the membership row


def list_tenant_members(db: Session, *, tenant_id: uuid.UUID) -> list[TenantMember]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.tenant_id == tenant_id)
        .order_by(Membership.created_at)
    ).all()
    return [
        TenantMember(
            membership_id=m.id,
            user_id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=m.role,
            member_since=m.created_at.isoformat(),
        )
        for (m, u) in rows
    ]


def _get_tenant_membership(
    db: Session, *, tenant_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership:
    membership = db.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise NotFound("membership not found")
    return membership


def _assert_not_last_owner(db: Session, *, tenant_id: uuid.UUID, membership: Membership) -> None:
    """A tenant must retain at least one OWNER — otherwise nobody can administer it."""
    if membership.role != Role.OWNER:
        return
    owners = db.execute(
        select(func.count())
        .select_from(Membership)
        .where(Membership.tenant_id == tenant_id, Membership.role == Role.OWNER)
    ).scalar_one()
    if owners <= 1:
        raise Conflict("tenant requires at least one owner")


def change_member_role(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    membership_id: uuid.UUID,
    new_role: Role,
    acting_user_id: uuid.UUID,
) -> tuple[Membership, Role]:
    """Change a member's role. Returns (membership, old_role).

    Guards: no self-target (an owner cannot demote themselves — prevents accidental
    lock-out and keeps every change attributable to ANOTHER owner), and the tenant must
    keep at least one owner."""
    membership = _get_tenant_membership(db, tenant_id=tenant_id, membership_id=membership_id)
    if membership.user_id == acting_user_id:
        raise Conflict("cannot modify own membership")
    old_role = membership.role
    if old_role == new_role:
        return membership, old_role
    if new_role != Role.OWNER:
        _assert_not_last_owner(db, tenant_id=tenant_id, membership=membership)
    membership.role = new_role
    db.flush()
    return membership, old_role


def remove_member(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    membership_id: uuid.UUID,
    acting_user_id: uuid.UUID,
) -> Role:
    """Remove a member from the tenant (the User row remains; only the Membership goes).

    Same guards as change_member_role. Returns the removed member's role for the audit."""
    membership = _get_tenant_membership(db, tenant_id=tenant_id, membership_id=membership_id)
    if membership.user_id == acting_user_id:
        raise Conflict("cannot modify own membership")
    _assert_not_last_owner(db, tenant_id=tenant_id, membership=membership)
    removed_role = membership.role
    db.delete(membership)
    db.flush()
    return removed_role
