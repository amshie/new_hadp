"""Deletion-request application service — the request lifecycle (no execution here).

All reads/writes are tenant-scoped (explicit filter + RLS). The two-person gate is enforced
here in the service (the API layer only checks the role): the DECIDER must differ from the
REQUESTER, decisions apply only to a `pending` request, and at most one non-terminal request
may exist per patient. The irreversible erasure that consumes an `approved` request is a
separate slice (docs/notes/0012, PR B).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.enums import DeletionReasonCategory, DeletionRequestStatus
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy.models import DeletionRequest

# Requests in these states still "occupy" a patient; a new request is refused while one exists.
_NON_TERMINAL = (DeletionRequestStatus.PENDING, DeletionRequestStatus.APPROVED)


def _get_request(db: Session, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> DeletionRequest:
    req = db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id, DeletionRequest.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if req is None:
        raise NotFound("deletion request not found")
    return req


def create_request(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    reason_category: DeletionReasonCategory,
    requested_by_user_id: uuid.UUID,
) -> DeletionRequest:
    """Open a pending erasure request for a patient.

    Verifies the patient exists in THIS tenant (a cross-tenant id is a 404, no info leak) and
    refuses a second non-terminal request for the same patient (409). The DB also carries a
    partial unique index as the backstop against a race.
    """
    # Tenant-scoped existence check (raises NotFound on a cross-tenant / unknown id).
    patient = db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if patient is None:
        raise NotFound("patient not found")

    existing = db.execute(
        select(DeletionRequest).where(
            DeletionRequest.tenant_id == tenant_id,
            DeletionRequest.patient_id == patient_id,
            DeletionRequest.status.in_(_NON_TERMINAL),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("an open deletion request already exists for this patient")

    req = DeletionRequest(
        tenant_id=tenant_id,
        patient_id=patient_id,
        status=DeletionRequestStatus.PENDING,
        reason_category=reason_category,
        requested_by_user_id=requested_by_user_id,
        requested_at=datetime.now(UTC),
    )
    db.add(req)
    db.flush()
    return req


def list_requests(db: Session, *, tenant_id: uuid.UUID) -> list[DeletionRequest]:
    return list(
        db.execute(
            select(DeletionRequest)
            .where(DeletionRequest.tenant_id == tenant_id)
            .order_by(DeletionRequest.requested_at.desc())
        )
        .scalars()
        .all()
    )


def decide_request(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
    approve: bool,
    deciding_user_id: uuid.UUID,
) -> DeletionRequest:
    """Approve or reject a pending request (medical director).

    Two-person guard: the decider must differ from the requester (defense-in-depth — the
    role split already guarantees it, since a user holds one role per tenant). Only a
    `pending` request can be decided.
    """
    req = _get_request(db, tenant_id=tenant_id, request_id=request_id)
    if req.status != DeletionRequestStatus.PENDING:
        raise Conflict("only a pending request can be decided")
    if req.requested_by_user_id == deciding_user_id:
        raise Conflict("the requester may not decide their own request")
    req.status = DeletionRequestStatus.APPROVED if approve else DeletionRequestStatus.REJECTED
    req.decided_by_user_id = deciding_user_id
    req.decided_at = datetime.now(UTC)
    db.flush()
    return req


def cancel_request(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
    acting_user_id: uuid.UUID,
) -> DeletionRequest:
    """Cancel a still-pending request. Only the original requester may cancel."""
    req = _get_request(db, tenant_id=tenant_id, request_id=request_id)
    if req.status != DeletionRequestStatus.PENDING:
        raise Conflict("only a pending request can be cancelled")
    if req.requested_by_user_id != acting_user_id:
        raise Conflict("only the requester may cancel this request")
    req.status = DeletionRequestStatus.CANCELLED
    db.flush()
    return req
