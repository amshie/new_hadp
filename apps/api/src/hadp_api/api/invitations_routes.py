"""Patient-invitation routes (P1/P2, docs/notes/0010 §4–5). Synthetic identities only.

Create is staff-side (cookie-auth, rate-limited, audited WITHOUT the token; the raw
token is returned once for the synthetic manual-share flow — no automatic delivery
exists). Redeem is patient-side: NO staff session; the token travels in the POST BODY
(never a query string — P-pre-3) and is the sole credential; the tenant id in the body
is non-secret and only binds RLS scope. Every non-redeemable state is the same 404,
audited as an `invitation.redeem_denied` security event. Redemption appends the
GRANTED report_release consent event the P0 release gate consumes — real-patient use
stays BLOCKED behind the register's pending human gates.
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
from hadp_api.modules.invitations import service as invitations_service
from hadp_api.modules.patients import service as patients_service
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(tags=["invitations"])


class InvitationOut(BaseModel):
    invitation_id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    expires_at: str
    # Synthetic-Alpha manual-share flow ONLY: the raw token/URL appear exactly once,
    # in this response. Nothing is delivered automatically.
    invitation_token: str
    invitation_url: str


class RedeemIn(BaseModel):
    tenant: uuid.UUID
    token: str = Field(min_length=1, max_length=128)


class RedeemOut(BaseModel):
    status: str
    purpose: str


@router.post("/patients/{patient_id}/invitations", response_model=InvitationOut, status_code=201)
def create_invitation(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INVITATION_CREATE)),
) -> InvitationOut:
    check_rate_limit(
        action="invitation.create",
        key=str(ctx.user.id),
        limit=30,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
    # Tenant-scoped existence check: a cross-tenant patient_id is a 404 (no info leak).
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    invitation, raw_token = invitations_service.create_invitation(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        created_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="invitation.create",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient_invitation",
        target_id=invitation.id,
        correlation_id=ctx.correlation_id,
        # Never the token — identifiers only.
        detail={"status": invitation.status.value},
    )
    # The manual-share web link carries tenant + token (like the patient-view link);
    # the API-side redeem still takes the token in the POST body only (P-pre-3).
    base = get_settings().web_base_url
    return InvitationOut(
        invitation_id=invitation.id,
        patient_id=invitation.patient_id,
        status=invitation.status.value,
        expires_at=invitation.expires_at.isoformat(),
        invitation_token=raw_token,
        invitation_url=f"{base}/einladung?tenant={ctx.tenant_id}&token={raw_token}",
    )


@router.post("/invitations/{invitation_id}/revoke")
def revoke_invitation(
    invitation_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INVITATION_CREATE)),
) -> dict[str, str]:
    invitation = invitations_service.revoke_invitation(
        ctx.db, tenant_id=ctx.tenant_id, invitation_id=invitation_id
    )
    record_audit(
        ctx.db,
        action="invitation.revoked",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient_invitation",
        target_id=invitation.id,
        correlation_id=ctx.correlation_id,
        detail={"status": invitation.status.value},
    )
    return {"status": invitation.status.value}


@router.post("/invitations/redeem", response_model=RedeemOut)
def redeem_invitation(
    body: RedeemIn,
    request: Request,
    db: Session = RequestSession,
) -> RedeemOut:
    # Public token surface: throttle per client IP before touching the database.
    check_rate_limit(
        action="invitation.redeem",
        key=request.client.host if request.client else "unknown",
        limit=30,
        window_seconds=60,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    # Bind tenant scope from the body (non-secret); the token is the credential.
    set_tenant_context(db, body.tenant)
    try:
        invitation = invitations_service.redeem_invitation(
            db, tenant_id=body.tenant, raw_token=body.token
        )
    except NotFound:
        record_security_event(
            action="invitation.redeem_denied",
            tenant_id=body.tenant,
            correlation_id=getattr(request.state, "correlation_id", None),
            detail={"reason": "not_found"},
        )
        raise
    record_audit(
        db,
        action="invitation.redeemed",
        tenant_id=body.tenant,
        target_type="patient_invitation",
        target_id=invitation.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        detail={"purpose": "report_release"},
    )
    return RedeemOut(status=invitation.status.value, purpose="report_release")
