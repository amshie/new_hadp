"""Authentication routes.

`dev-login` is a development/test convenience that resolves a seeded synthetic user
with no credential check; it is disabled in production, where OIDC handles login.
"""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hadp_api.api.schemas import TenantMembershipOut, UserOut
from hadp_api.auth.dependencies import Principal, get_correlation_id, get_current_principal
from hadp_api.auth.provider import get_auth_provider
from hadp_api.auth.sessions import create_session, revoke_session
from hadp_api.config import get_settings
from hadp_api.db.session import get_db
from hadp_api.errors import NotAuthenticated, NotFound
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.service import get_membership, list_memberships
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    user: UserOut
    tenants: list[TenantMembershipOut]


class MeResponse(BaseModel):
    user: UserOut
    active_tenant_id: uuid.UUID | None
    role: Role | None


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    """Double-submit CSRF token (P-pre-2): deliberately NOT httpOnly — the legitimate
    client must be able to read it back into the `x-csrf-token` header; it grants no
    access by itself (the session cookie stays httpOnly)."""
    settings = get_settings()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


@router.post("/dev-login", response_model=LoginResponse)
def dev_login(
    body: DevLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> LoginResponse:
    settings = get_settings()
    if settings.is_production:
        # Do not reveal the existence of the dev endpoint in production.
        raise NotFound("not found")
    # Login is the classic brute-force surface — throttle per client IP (P-pre-1).
    check_rate_limit(
        action="auth.dev_login",
        key=request.client.host if request.client else "unknown",
        limit=10,
        window_seconds=60,
        correlation_id=correlation_id,
    )

    provider = get_auth_provider(settings)
    user = provider.resolve_user(db, body.email)
    if user is None:
        # Failed logins are audited (independent transaction — survives the 401 path).
        # Detail carries a reason code only, never the attempted identifier.
        record_security_event(
            action="login.failed",
            correlation_id=correlation_id,
            detail={"reason": "unknown_user"},
        )
        raise NotAuthenticated("unknown user")

    _, raw_token = create_session(db, user_id=user.id, ttl_seconds=settings.session_ttl_seconds)
    _set_session_cookie(response, raw_token)
    _set_csrf_cookie(response, secrets.token_urlsafe(32))
    record_audit(
        db,
        action="auth.dev_login",
        actor_user_id=user.id,
        correlation_id=correlation_id,
        detail={"provider": provider.name},
    )
    memberships = list_memberships(db, user.id)
    return LoginResponse(
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
        tenants=[TenantMembershipOut(**m.__dict__) for m in memberships],
    )


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> Response:
    revoke_session(db, principal.session)
    record_audit(
        db,
        action="auth.logout",
        actor_user_id=principal.user.id,
        correlation_id=correlation_id,
    )
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MeResponse:
    active = principal.session.active_tenant_id
    role: Role | None = None
    if active is not None:
        membership = get_membership(db, principal.user.id, active)
        role = membership.role if membership else None
    return MeResponse(
        user=UserOut(
            id=principal.user.id,
            email=principal.user.email,
            display_name=principal.user.display_name,
        ),
        active_tenant_id=active,
        role=role,
    )
