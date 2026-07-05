"""Deletion-request application service — the request lifecycle (no execution here).

All reads/writes are tenant-scoped (explicit filter + RLS). The two-person gate is enforced
here in the service (the API layer only checks the role): the DECIDER must differ from the
REQUESTER, decisions apply only to a `pending` request, and at most one non-terminal request
may exist per patient. The irreversible erasure that consumes an `approved` request is a
separate slice (docs/notes/0012, PR B).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import (
    ConsentPurpose,
    DeletionReasonCategory,
    DeletionRequestStatus,
    InvitationStatus,
)
from hadp_api.modules.imports.models import ImportJob
from hadp_api.modules.interpretation.models import InterpretationRun
from hadp_api.modules.invitations.models import PatientInvitation
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy.models import DeletionRequest
from hadp_api.modules.reports.models import Report

# Requests in these states still "occupy" a patient; a new request is refused while one exists.
_NON_TERMINAL = (DeletionRequestStatus.PENDING, DeletionRequestStatus.APPROVED)

# Anonymized display name written to a tombstoned patient row (identity is otherwise blanked).
TOMBSTONE_NAME = "[Gelöschter Datensatz]"


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


@dataclass(frozen=True)
class ErasureResult:
    request: DeletionRequest
    manifest: dict[str, int]
    # Object-storage keys to purge AFTER the DB transaction commits (S3 delete is not
    # transactional; a partial failure is re-runnable and separately audited).
    storage_keys: list[str]


def _count(db: Session, model: Any, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(model)
            .where(model.tenant_id == tenant_id, model.patient_id == patient_id)
        ).scalar_one()
    )


def execute_request(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
    executing_user_id: uuid.UUID,
) -> ErasureResult:
    """Irreversibly erase a patient's data for an APPROVED request (gated tombstone).

    Anonymizes the patient row and hard-deletes PII-bearing artifacts, while PRESERVING the
    append-only ledgers: consent events get an appended WITHDRAWN event (never deleted), audit
    events are untouched, and interpretation runs/cells are kept with their free text redacted.
    Runs in the caller's single request transaction (atomic); the caller purges object storage
    AFTER commit using the returned keys.

    Guards: the request must be `approved` (else 409) and the patient must not already be erased
    (idempotency guard, else 409). Everything is tenant-scoped (explicit filter + RLS).
    """
    req = _get_request(db, tenant_id=tenant_id, request_id=request_id)
    if req.status != DeletionRequestStatus.APPROVED:
        raise Conflict("only an approved request can be executed")
    patient = db.execute(
        select(Patient).where(Patient.id == req.patient_id, Patient.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if patient is None:
        raise NotFound("patient not found")
    if patient.erased_at is not None:
        raise Conflict("patient is already erased")

    pid = patient.id
    # Counts for the manifest (identifiers/values never recorded — counts only).
    manifest: dict[str, int] = {
        "observations": _count(db, Observation, tenant_id=tenant_id, patient_id=pid),
        "documents": _count(db, SourceDocument, tenant_id=tenant_id, patient_id=pid),
        "reports": _count(db, Report, tenant_id=tenant_id, patient_id=pid),
        "import_jobs": _count(db, ImportJob, tenant_id=tenant_id, patient_id=pid),
        "interpretation_runs": _count(db, InterpretationRun, tenant_id=tenant_id, patient_id=pid),
    }
    storage_keys = list(
        db.execute(
            select(SourceDocument.storage_key).where(
                SourceDocument.tenant_id == tenant_id, SourceDocument.patient_id == pid
            )
        )
        .scalars()
        .all()
    )

    # 1) Append-only-touching work goes through the gated SECURITY DEFINER primitive: delete the
    #    derivation lineage that references this patient's observations, and redact interpretation
    #    free text. (consent_events / audit_events triggers are never involved.)
    db.execute(
        text("SELECT hadp_execute_patient_erasure(:t, :p)"),
        {"t": str(tenant_id), "p": str(pid)},
    )

    # 2) Withdraw every currently-active consent (append-only WITHDRAWN event; withdrawing
    #    report_release also revokes live patient access links in the same transaction).
    withdrawn = 0
    for purpose in ConsentPurpose:
        if consents_service.has_active_consent(
            db, tenant_id=tenant_id, patient_id=pid, purpose=purpose
        ):
            consents_service.withdraw_consent(
                db,
                tenant_id=tenant_id,
                patient_id=pid,
                purpose=purpose,
                channel="erasure",
                recorded_by_user_id=executing_user_id,
            )
            withdrawn += 1
    manifest["consents_withdrawn"] = withdrawn

    # 3) Revoke any open (pending) invitations.
    open_invites = int(
        db.execute(
            select(func.count())
            .select_from(PatientInvitation)
            .where(
                PatientInvitation.tenant_id == tenant_id,
                PatientInvitation.patient_id == pid,
                PatientInvitation.status == InvitationStatus.PENDING,
            )
        ).scalar_one()
    )
    if open_invites:
        db.execute(
            update(PatientInvitation)
            .where(
                PatientInvitation.tenant_id == tenant_id,
                PatientInvitation.patient_id == pid,
                PatientInvitation.status == InvitationStatus.PENDING,
            )
            .values(status=InvitationStatus.REVOKED, revoked_at=datetime.now(UTC))
        )
    manifest["invitations_revoked"] = open_invites

    # 4) Hard-delete PII-bearing mutable artifacts (DB FK cascades handle their children:
    #    reports -> versions/evidence/access-links; import_jobs -> rows/review-items; observations
    #    -> review-items). Derivation lineage was already removed in step 1, so observations delete
    #    cleanly. Reports go before observations so their evidence rows are gone first.
    db.execute(delete(Report).where(Report.tenant_id == tenant_id, Report.patient_id == pid))
    db.execute(
        delete(Observation).where(Observation.tenant_id == tenant_id, Observation.patient_id == pid)
    )
    db.execute(
        delete(ImportJob).where(ImportJob.tenant_id == tenant_id, ImportJob.patient_id == pid)
    )
    db.execute(
        delete(SourceDocument).where(
            SourceDocument.tenant_id == tenant_id, SourceDocument.patient_id == pid
        )
    )

    # 5) Tombstone the patient: blank identity, keep the row (FKs from the preserved ledgers
    #    point here; the row now carries no identity).
    patient.display_name = TOMBSTONE_NAME
    patient.date_of_birth = None
    patient.external_ref = None
    patient.erased_at = datetime.now(UTC)

    # 6) Close out the request.
    req.status = DeletionRequestStatus.EXECUTED
    req.executed_by_user_id = executing_user_id
    req.executed_at = datetime.now(UTC)
    req.erasure_manifest = manifest
    db.flush()
    return ErasureResult(request=req, manifest=manifest, storage_keys=storage_keys)
