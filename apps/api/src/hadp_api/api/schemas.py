"""Shared API response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from hadp_api.modules.enums import Role


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str


class TenantMembershipOut(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    is_synthetic: bool
    role: Role
