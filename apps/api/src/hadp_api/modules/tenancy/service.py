"""Tenancy application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import Role
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
