"""Member-administration routes: list the clinic team, change a role, remove a member.

OWNER-only via the deny-by-default matrix (MEMBER_LIST / MEMBER_ROLE_CHANGE / MEMBER_REMOVE).
`memberships` is a non-RLS table, so the service scopes every query by tenant_id explicitly;
a cross-tenant membership id resolves to the same 404 as an unknown one. Guards live in the
service: no self-target, and the tenant must keep at least one owner. Sensitive transitions
are audited with role codes only — never a name or email. Role assignment is orthogonal to
the two-tier Physician Gate (enforced at action time by the assigned role).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy import service as tenancy_service

router = APIRouter(tags=["members"])


class MemberOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: Role
    member_since: str


class RoleChangeIn(BaseModel):
    # Closed role vocabulary: an invented value is rejected at the boundary (422).
    role: Role


@router.get("/members", response_model=list[MemberOut])
def list_members(
    ctx: TenantContext = Depends(require(Action.MEMBER_LIST)),
) -> list[MemberOut]:
    members = tenancy_service.list_tenant_members(ctx.db, tenant_id=ctx.tenant_id)
    return [MemberOut(**m.__dict__) for m in members]


@router.patch("/members/{membership_id}", response_model=MemberOut)
def change_member_role(
    membership_id: uuid.UUID,
    body: RoleChangeIn,
    ctx: TenantContext = Depends(require(Action.MEMBER_ROLE_CHANGE)),
) -> MemberOut:
    membership, old_role = tenancy_service.change_member_role(
        ctx.db,
        tenant_id=ctx.tenant_id,
        membership_id=membership_id,
        new_role=body.role,
        acting_user_id=ctx.user.id,
    )
    if old_role != membership.role:
        record_audit(
            ctx.db,
            action="member.role_changed",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            target_type="membership",
            target_id=membership.id,
            correlation_id=ctx.correlation_id,
            # Role codes only — never the member's name or email.
            detail={"old_role": old_role.value, "new_role": membership.role.value},
        )
    # Re-read through the list projection so the response shape stays single-sourced.
    members = tenancy_service.list_tenant_members(ctx.db, tenant_id=ctx.tenant_id)
    updated = next(m for m in members if m.membership_id == membership.id)
    return MemberOut(**updated.__dict__)


@router.delete("/members/{membership_id}")
def remove_member(
    membership_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.MEMBER_REMOVE)),
) -> dict[str, str]:
    removed_role = tenancy_service.remove_member(
        ctx.db,
        tenant_id=ctx.tenant_id,
        membership_id=membership_id,
        acting_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="member.removed",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="membership",
        target_id=membership_id,
        correlation_id=ctx.correlation_id,
        detail={"removed_role": removed_role.value},
    )
    return {"status": "removed"}
