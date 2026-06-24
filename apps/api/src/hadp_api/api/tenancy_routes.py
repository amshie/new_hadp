"""Tenancy routes: list accessible tenants and select an active tenant."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hadp_api.api.schemas import TenantMembershipOut
from hadp_api.auth.dependencies import Principal, get_correlation_id, get_current_principal
from hadp_api.db.engine import set_tenant_context
from hadp_api.db.session import get_db
from hadp_api.errors import PermissionDenied
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.service import get_membership, list_memberships

router = APIRouter(prefix="/tenancy", tags=["tenancy"])


class SelectTenantRequest(BaseModel):
    tenant_id: uuid.UUID


class SelectTenantResponse(BaseModel):
    active_tenant_id: uuid.UUID
    role: Role


@router.get("/my-tenants", response_model=list[TenantMembershipOut])
def my_tenants(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[TenantMembershipOut]:
    memberships = list_memberships(db, principal.user.id)
    return [TenantMembershipOut(**m.__dict__) for m in memberships]


@router.post("/select-tenant", response_model=SelectTenantResponse)
def select_tenant(
    body: SelectTenantRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> SelectTenantResponse:
    membership = get_membership(db, principal.user.id, body.tenant_id)
    if membership is None:
        # Deny-by-default: cannot select a tenant you are not a member of.
        raise PermissionDenied("not a member of the requested tenant")

    # Bind tenant scope so the tenant-attributed audit insert satisfies RLS.
    set_tenant_context(db, body.tenant_id, principal.user.id)
    principal.session.active_tenant_id = body.tenant_id
    record_audit(
        db,
        action="tenant.select",
        actor_user_id=principal.user.id,
        tenant_id=body.tenant_id,
        target_type="tenant",
        target_id=body.tenant_id,
        correlation_id=correlation_id,
        detail={"role": membership.role.value},
    )
    return SelectTenantResponse(active_tenant_id=body.tenant_id, role=membership.role)
