"""Staff-invitation routes: a clinic OWNER invites a colleague who self-onboards.

Create/list/revoke are owner-side (cookie-auth, OWNER-only via STAFF_INVITE_CREATE, rate-
limited, audited WITHOUT the token; the raw token is returned once for the synthetic manual-
share flow). Redeem is colleague-side: NO staff session; the token travels in the POST BODY
(never a query string) and is the sole credential; the tenant id in the body is non-secret and
only binds RLS scope. Redemption creates the colleague's User + Membership with the ROLE the
owner fixed — the redeemer never chooses it. Every non-redeemable state is the same 404,
audited as a `staff_invite.redeem_denied` security event. Synthetic identities only.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.config import get_settings
from hadp_api.db.engine import set_tenant_context
from hadp_api.db.session import RequestSession
from hadp_api.errors import NotFound
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.enums import Role
from hadp_api.modules.staff_invitations import service as staff_invitations_service
from hadp_api.security.client_address import client_address
from hadp_api.security.rate_limit import (
    REFUSAL_WINDOW_SECONDS,
    REFUSALS_RECORDED,
    check_rate_limit,
    refusal_recording,
)

router = APIRouter(tags=["staff-invitations"])


class StaffInviteCreateIn(BaseModel):
    # Closed role vocabulary: an invented value is rejected at the boundary (422).
    role: Role


class StaffInvitationOut(BaseModel):
    invitation_id: uuid.UUID
    role: Role
    status: str
    expires_at: str
    # Synthetic-Alpha manual-share flow ONLY: the raw token/URL appear exactly once, here.
    invitation_token: str
    invitation_url: str


class StaffInvitationListItem(BaseModel):
    invitation_id: uuid.UUID
    role: Role
    status: str
    expires_at: str
    created_at: str


class StaffRedeemIn(BaseModel):
    tenant: uuid.UUID
    token: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    # Light constraint only (a strict RFC validator would add a dependency); the address is
    # normalized (trimmed + lowercased) in the service and is synthetic-Alpha data.
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class StaffRedeemOut(BaseModel):
    status: str
    role: Role


@router.post("/staff-invitations", response_model=StaffInvitationOut, status_code=201)
def create_staff_invitation(
    body: StaffInviteCreateIn,
    ctx: TenantContext = Depends(require(Action.STAFF_INVITE_CREATE)),
) -> StaffInvitationOut:
    check_rate_limit(
        action="staff_invite.create",
        key=str(ctx.user.id),
        limit=30,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
    invitation, raw_token = staff_invitations_service.create_staff_invitation(
        ctx.db,
        tenant_id=ctx.tenant_id,
        role=body.role,
        created_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="staff_invite.create",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="staff_invitation",
        target_id=invitation.id,
        correlation_id=ctx.correlation_id,
        # Role code + status only — never the token, name, or email.
        detail={"role": invitation.role.value, "status": invitation.status.value},
    )
    base = get_settings().web_base_url
    return StaffInvitationOut(
        invitation_id=invitation.id,
        role=invitation.role,
        status=invitation.status.value,
        expires_at=invitation.expires_at.isoformat(),
        invitation_token=raw_token,
        invitation_url=f"{base}/team-einladung?tenant={ctx.tenant_id}&token={raw_token}",
    )


@router.get("/staff-invitations", response_model=list[StaffInvitationListItem])
def list_staff_invitations(
    ctx: TenantContext = Depends(require(Action.STAFF_INVITE_CREATE)),
) -> list[StaffInvitationListItem]:
    invitations = staff_invitations_service.list_staff_invitations(ctx.db, tenant_id=ctx.tenant_id)
    return [
        StaffInvitationListItem(
            invitation_id=inv.id,
            role=inv.role,
            status=inv.status.value,
            expires_at=inv.expires_at.isoformat(),
            created_at=inv.created_at.isoformat(),
        )
        for inv in invitations
    ]


@router.post("/staff-invitations/{invitation_id}/revoke")
def revoke_staff_invitation(
    invitation_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.STAFF_INVITE_CREATE)),
) -> dict[str, str]:
    invitation = staff_invitations_service.revoke_staff_invitation(
        ctx.db, tenant_id=ctx.tenant_id, invitation_id=invitation_id
    )
    record_audit(
        ctx.db,
        action="staff_invite.revoked",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="staff_invitation",
        target_id=invitation.id,
        correlation_id=ctx.correlation_id,
        detail={"status": invitation.status.value},
    )
    return {"status": invitation.status.value}


@router.post("/staff-invitations/redeem", response_model=StaffRedeemOut)
def redeem_staff_invitation(
    body: StaffRedeemIn,
    request: Request,
    db: Session = RequestSession,
) -> StaffRedeemOut:
    # Public token surface: throttle per client address before touching the database.
    check_rate_limit(
        action="staff_invite.redeem",
        key=client_address(request),
        limit=30,
        window_seconds=60,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    # Bind tenant scope from the body (non-secret); the token is the credential.
    set_tenant_context(db, body.tenant)
    try:
        invitation, _user, membership = staff_invitations_service.redeem_staff_invitation(
            db,
            tenant_id=body.tenant,
            raw_token=body.token,
            display_name=body.display_name,
            email=body.email,
        )
    except NotFound:
        # As much of it as a clinic's trail takes from callers without a session.
        recording = refusal_recording(surface="staff_invite.redeem", tenant_id=body.tenant)
        if recording == "each":
            record_security_event(
                action="staff_invite.redeem_denied",
                tenant_id=body.tenant,
                correlation_id=getattr(request.state, "correlation_id", None),
                detail={"reason": "not_found"},
            )
        elif recording == "stops":
            record_security_event(
                action="staff_invite.redeem_denials_unrecorded",
                tenant_id=body.tenant,
                correlation_id=getattr(request.state, "correlation_id", None),
                detail={"recorded": REFUSALS_RECORDED, "window_seconds": REFUSAL_WINDOW_SECONDS},
            )
        raise
    record_audit(
        db,
        action="staff_invite.redeemed",
        tenant_id=body.tenant,
        target_type="membership",
        target_id=membership.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        # Role code only — never the colleague's name or email.
        detail={"role": membership.role.value},
    )
    return StaffRedeemOut(status=invitation.status.value, role=membership.role)
