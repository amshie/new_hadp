"""FastAPI auth/tenant dependencies.

Every tenant-scoped request resolves an authenticated principal and an active tenant
the principal is a member of, then binds the tenant to the DB transaction so RLS
applies. Authorization is checked against the deny-by-default matrix.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.auth.authz import Action, can
from hadp_api.auth.sessions import get_active_session
from hadp_api.config import get_settings
from hadp_api.db.engine import set_tenant_context
from hadp_api.db.session import get_db
from hadp_api.errors import NotAuthenticated, PermissionDenied
from hadp_api.modules.audit.service import record_security_event
from hadp_api.modules.enums import Role
from hadp_api.modules.identity.models import AuthSession, User
from hadp_api.modules.tenancy.models import Membership


@dataclass
class Principal:
    user: User
    session: AuthSession


@dataclass
class TenantContext:
    db: Session
    user: User
    tenant_id: uuid.UUID
    role: Role
    correlation_id: str


def get_correlation_id(request: Request) -> str:
    value = getattr(request.state, "correlation_id", None)
    return value if isinstance(value, str) else "unknown"


def get_current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise NotAuthenticated("no session")
    session = get_active_session(db, token)
    if session is None:
        raise NotAuthenticated("invalid or expired session")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise NotAuthenticated("user inactive")
    return Principal(user=user, session=session)


def get_tenant_context(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> TenantContext:
    tenant_id = principal.session.active_tenant_id
    if tenant_id is None:
        record_security_event(
            action="authz.denied",
            actor_user_id=principal.user.id,
            correlation_id=correlation_id,
            detail={"reason": "no_active_tenant"},
        )
        raise PermissionDenied("no active tenant selected")
    membership = db.execute(
        select(Membership).where(
            Membership.user_id == principal.user.id,
            Membership.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        record_security_event(
            action="authz.denied",
            actor_user_id=principal.user.id,
            correlation_id=correlation_id,
            detail={"reason": "not_a_member", "attempted_tenant": str(tenant_id)},
        )
        raise PermissionDenied("not a member of the active tenant")
    # Bind tenant scope to the transaction so RLS applies to every later query.
    set_tenant_context(db, tenant_id, principal.user.id)
    return TenantContext(
        db=db,
        user=principal.user,
        tenant_id=tenant_id,
        role=membership.role,
        correlation_id=correlation_id,
    )


def require(action: Action) -> Callable[[TenantContext], TenantContext]:
    """Dependency factory: require the active role to be permitted for `action`."""

    def _dep(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not can(ctx.role, action):
            record_security_event(
                action="authz.denied",
                actor_user_id=ctx.user.id,
                tenant_id=ctx.tenant_id,
                correlation_id=ctx.correlation_id,
                detail={"reason": "role_not_permitted", "attempted": action.value},
            )
            raise PermissionDenied(f"role '{ctx.role.value}' may not perform '{action.value}'")
        return ctx

    return _dep
