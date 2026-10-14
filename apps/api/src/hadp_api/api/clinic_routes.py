"""The clinic's own profile: its name and address (Einstellungen › Praxisprofil).

Every staff role reads it; the owner changes it (TENANT_PROFILE_EDIT). `tenants` is a table
without row-level security, so every statement names the caller's own tenant explicitly. A
change is recorded with the names of the fields that changed — never their values. The time
zone in which laboratory times are read is a setting of the platform, shown, not changed here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.config import get_settings
from hadp_api.errors import NotFound
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.tenancy.models import Tenant

router = APIRouter(tags=["clinic"])


class ClinicProfileOut(BaseModel):
    name: str
    address: str | None
    # The zone laboratory times without one are read in (LAB_LOCAL_TIMEZONE).
    lab_time_zone: str
    is_synthetic: bool


class ClinicProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def _name_is_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("a name is required")
        return value

    @field_validator("address")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None


def _own(ctx: TenantContext) -> Tenant:
    tenant = ctx.db.get(Tenant, ctx.tenant_id)
    if tenant is None:
        raise NotFound("clinic not found")
    return tenant


def _out(tenant: Tenant) -> ClinicProfileOut:
    return ClinicProfileOut(
        name=tenant.name,
        address=tenant.address,
        lab_time_zone=get_settings().lab_local_timezone,
        is_synthetic=tenant.is_synthetic,
    )


@router.get("/clinic-profile", response_model=ClinicProfileOut)
def read_clinic_profile(
    ctx: TenantContext = Depends(require(Action.TENANT_PROFILE_READ)),
) -> ClinicProfileOut:
    tenant = _own(ctx)
    record_audit(
        ctx.db,
        action="tenant.profile.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
    )
    return _out(tenant)


@router.put("/clinic-profile", response_model=ClinicProfileOut)
def change_clinic_profile(
    body: ClinicProfileIn,
    ctx: TenantContext = Depends(require(Action.TENANT_PROFILE_EDIT)),
) -> ClinicProfileOut:
    tenant = _own(ctx)
    changed = [
        field
        for field, before, after in (
            ("name", tenant.name, body.name),
            ("address", tenant.address, body.address),
        )
        if before != after
    ]
    tenant.name = body.name
    tenant.address = body.address
    ctx.db.flush()
    if changed:
        record_audit(
            ctx.db,
            action="tenant.profile_changed",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
            # Which fields changed — never what they say.
            detail={"changed": changed},
        )
    return _out(tenant)
