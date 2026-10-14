"""Authentication routes.

`dev-login` is a development/test convenience that resolves a seeded synthetic user
with no credential check; it is disabled in production, where OIDC handles login.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hadp_api.api.schemas import TenantMembershipOut, UserOut
from hadp_api.auth.dependencies import Principal, get_correlation_id, get_current_principal
from hadp_api.auth.provider import get_auth_provider
from hadp_api.auth.sessions import (
    create_session,
    list_user_sessions,
    revoke_other_sessions,
    revoke_session,
)
from hadp_api.config import get_settings
from hadp_api.db.session import RequestSession
from hadp_api.errors import NotAuthenticated, NotFound
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.enums import Role
from hadp_api.modules.tenancy.models import Tenant
from hadp_api.modules.tenancy.service import get_membership, list_memberships
from hadp_api.security.client_address import client_address
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
    active_tenant_name: str | None
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


def _clear_auth_cookies(response: Response) -> None:
    """Sign-out removes BOTH cookies, each with the attributes it was set with.

    A browser applies a deletion only if it would accept the cookie: a `__Host-` name (the
    production names) is refused without `Secure` and `Path=/`, so a deletion that leaves
    them out removes nothing. The session is revoked server-side either way. Today's web app
    calls this API from its own server and keeps the two values in cookies of its own, which
    it removes itself (apps/web/src/lib/api.ts) — these headers are for a client that holds
    the API's cookies directly.
    """
    settings = get_settings()
    for name, httponly in (
        (settings.session_cookie_name, True),
        (settings.csrf_cookie_name, False),
    ):
        response.delete_cookie(
            key=name,
            path="/",
            secure=settings.is_production,
            httponly=httponly,
            samesite="lax",
        )


@router.post("/dev-login", response_model=LoginResponse)
def dev_login(
    body: DevLoginRequest,
    response: Response,
    request: Request,
    db: Session = RequestSession,
    correlation_id: str = Depends(get_correlation_id),
) -> LoginResponse:
    settings = get_settings()
    if settings.is_production:
        # Do not reveal the existence of the dev endpoint in production.
        raise NotFound("not found")
    # Login is the classic brute-force surface — throttle per client address (P-pre-1).
    check_rate_limit(
        action="auth.dev_login",
        key=client_address(request),
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
    db: Session = RequestSession,
    correlation_id: str = Depends(get_correlation_id),
) -> Response:
    revoke_session(db, principal.session)
    record_audit(
        db,
        action="auth.logout",
        actor_user_id=principal.user.id,
        correlation_id=correlation_id,
    )
    _clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(get_current_principal),
    db: Session = RequestSession,
) -> MeResponse:
    active = principal.session.active_tenant_id
    role: Role | None = None
    tenant_name: str | None = None
    if active is not None:
        membership = get_membership(db, principal.user.id, active)
        role = membership.role if membership else None
        tenant = db.get(Tenant, active)
        tenant_name = tenant.name if tenant else None
    return MeResponse(
        user=UserOut(
            id=principal.user.id,
            email=principal.user.email,
            display_name=principal.user.display_name,
        ),
        active_tenant_id=active,
        active_tenant_name=tenant_name,
        role=role,
    )


class SessionOut(BaseModel):
    id: uuid.UUID
    # In UTC.
    started_at: datetime
    expires_at: datetime
    # When it was signed out or ended from another session; null otherwise.
    ended_at: datetime | None
    state: Literal["active", "ended", "expired"]
    # The session this request came with.
    current: bool
    # The clinic last chosen in it, by name; null when none was chosen.
    clinic: str | None


class SessionsOut(BaseModel):
    # How this platform signs people in: "dev" (the password-less development sign-in) or
    # "oidc" (the clinic's sign-in service, which asks for the second factor).
    sign_in: str
    # The account's latest ten sessions, newest first.
    sessions: list[SessionOut]


class EndedOut(BaseModel):
    ended: int


@router.get("/sessions", response_model=SessionsOut)
def my_sessions(
    principal: Principal = Depends(get_current_principal),
    db: Session = RequestSession,
) -> SessionsOut:
    """One's own sessions: when each began, whether it still runs. No address, no device —
    the platform records neither."""
    now = datetime.now(UTC)
    names: dict[uuid.UUID, str] = {}
    out: list[SessionOut] = []
    for s in list_user_sessions(db, principal.user.id):
        clinic: str | None = None
        if s.active_tenant_id is not None:
            if s.active_tenant_id not in names:
                tenant = db.get(Tenant, s.active_tenant_id)
                names[s.active_tenant_id] = tenant.name if tenant else ""
            clinic = names[s.active_tenant_id] or None
        state: Literal["active", "ended", "expired"] = (
            "ended" if s.revoked_at is not None else "expired" if s.expires_at <= now else "active"
        )
        out.append(
            SessionOut(
                id=s.id,
                started_at=s.created_at.astimezone(UTC),
                expires_at=s.expires_at.astimezone(UTC),
                ended_at=s.revoked_at.astimezone(UTC) if s.revoked_at else None,
                state=state,
                current=s.id == principal.session.id,
                clinic=clinic,
            )
        )
    return SessionsOut(sign_in=get_auth_provider(get_settings()).name, sessions=out)


@router.post("/sessions/end-others", response_model=EndedOut)
def end_other_sessions(
    principal: Principal = Depends(get_current_principal),
    db: Session = RequestSession,
    correlation_id: str = Depends(get_correlation_id),
) -> EndedOut:
    """Sign out everywhere else: every other active session of this account ends now."""
    ended = revoke_other_sessions(db, user_id=principal.user.id, keep=principal.session.id)
    record_audit(
        db,
        action="auth.sessions_ended",
        actor_user_id=principal.user.id,
        correlation_id=correlation_id,
        detail={"count": ended},
    )
    return EndedOut(ended=ended)
