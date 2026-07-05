"""Patient-erasure request routes (tenant-scoped, RLS enforced, audited).

The request lifecycle of the two-person erasure gate (docs/notes/0012): an owner opens a
request, a medical director approves or rejects it, the requester may cancel a pending one.
The irreversible execution of an approved request is a SEPARATE slice — no execute route
exists here yet.

Every transition is audited with the request status / reason code only — never the patient's
name or any identity detail (the audit service's forbidden-key guard also rejects those keys).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import DeletionReasonCategory
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy import service as privacy_service
from hadp_api.modules.privacy.models import DeletionRequest

router = APIRouter(tags=["privacy"])


class DeletionRequestCreateIn(BaseModel):
    # Closed reason vocabulary (never free text) — an invented value is rejected at the
    # boundary (422), so the request row can never carry PII.
    reason_category: DeletionReasonCategory


class DeletionRequestOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    # Patient name for the management UI (authorized tenant staff already see patient names).
    # After execution the patient is tombstoned, so this reflects the anonymized value.
    patient_display_name: str
    patient_erased: bool
    status: str
    reason_category: str
    requested_by_user_id: uuid.UUID | None
    requested_at: str
    decided_by_user_id: uuid.UUID | None
    decided_at: str | None
    executed_at: str | None


def _out(req: DeletionRequest, patient: Patient) -> DeletionRequestOut:
    return DeletionRequestOut(
        id=req.id,
        patient_id=req.patient_id,
        patient_display_name=patient.display_name,
        patient_erased=patient.erased_at is not None,
        status=req.status.value,
        reason_category=req.reason_category.value,
        requested_by_user_id=req.requested_by_user_id,
        requested_at=req.requested_at.isoformat(),
        decided_by_user_id=req.decided_by_user_id,
        decided_at=req.decided_at.isoformat() if req.decided_at else None,
        executed_at=req.executed_at.isoformat() if req.executed_at else None,
    )


def _patient(ctx: TenantContext, patient_id: uuid.UUID) -> Patient:
    # Tenant-scoped fetch (explicit filter + RLS); a cross-tenant id is invisible.
    patient = ctx.db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == ctx.tenant_id)
    ).scalar_one_or_none()
    if patient is None:  # pragma: no cover - the service already guards create; defensive here
        from hadp_api.errors import NotFound

        raise NotFound("patient not found")
    return patient


@router.post(
    "/patients/{patient_id}/deletion-requests",
    response_model=DeletionRequestOut,
    status_code=201,
)
def create_deletion_request(
    patient_id: uuid.UUID,
    body: DeletionRequestCreateIn,
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_CREATE)),
) -> DeletionRequestOut:
    req = privacy_service.create_request(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        reason_category=body.reason_category,
        requested_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="privacy.deletion_requested",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="deletion_request",
        target_id=req.id,
        correlation_id=ctx.correlation_id,
        detail={"reason_category": req.reason_category.value},
    )
    return _out(req, _patient(ctx, patient_id))


@router.get("/deletion-requests", response_model=list[DeletionRequestOut])
def list_deletion_requests(
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_LIST)),
) -> list[DeletionRequestOut]:
    requests = privacy_service.list_requests(ctx.db, tenant_id=ctx.tenant_id)
    if not requests:
        return []
    patient_ids = {r.patient_id for r in requests}
    patients = {
        p.id: p
        for p in ctx.db.execute(
            select(Patient).where(Patient.id.in_(patient_ids), Patient.tenant_id == ctx.tenant_id)
        )
        .scalars()
        .all()
    }
    return [_out(r, patients[r.patient_id]) for r in requests if r.patient_id in patients]


@router.post("/deletion-requests/{request_id}/approve", response_model=DeletionRequestOut)
def approve_deletion_request(
    request_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_DECIDE)),
) -> DeletionRequestOut:
    req = privacy_service.decide_request(
        ctx.db,
        tenant_id=ctx.tenant_id,
        request_id=request_id,
        approve=True,
        deciding_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="privacy.deletion_approved",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="deletion_request",
        target_id=req.id,
        correlation_id=ctx.correlation_id,
    )
    return _out(req, _patient(ctx, req.patient_id))


@router.post("/deletion-requests/{request_id}/reject", response_model=DeletionRequestOut)
def reject_deletion_request(
    request_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_DECIDE)),
) -> DeletionRequestOut:
    req = privacy_service.decide_request(
        ctx.db,
        tenant_id=ctx.tenant_id,
        request_id=request_id,
        approve=False,
        deciding_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="privacy.deletion_rejected",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="deletion_request",
        target_id=req.id,
        correlation_id=ctx.correlation_id,
    )
    return _out(req, _patient(ctx, req.patient_id))


@router.post("/deletion-requests/{request_id}/cancel", response_model=DeletionRequestOut)
def cancel_deletion_request(
    request_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_CREATE)),
) -> DeletionRequestOut:
    # Cancelling one's own pending request is part of requesting — gated by the same
    # owner-only action; the service enforces requester-only + pending-only.
    req = privacy_service.cancel_request(
        ctx.db,
        tenant_id=ctx.tenant_id,
        request_id=request_id,
        acting_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="privacy.deletion_cancelled",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="deletion_request",
        target_id=req.id,
        correlation_id=ctx.correlation_id,
    )
    return _out(req, _patient(ctx, req.patient_id))
