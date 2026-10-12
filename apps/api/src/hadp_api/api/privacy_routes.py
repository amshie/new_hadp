"""Privacy routes: patient-erasure requests and the patient data export (tenant-scoped, RLS
enforced, audited).

Data export (GDPR Art. 15/20): an owner generates one package for one patient and downloads
it; nothing is stored. The audit event is its record (counts, size, checksum — never content).

The two-person erasure gate (docs/notes/0012): an owner opens a request, a medical director
approves or rejects it, the requester may cancel a pending one, and an owner or medical
director EXECUTES an approved request — the irreversible, gated tombstone erasure (the DB work
runs in this request's transaction; object storage is purged after commit).

Every transition is audited with the request status / reason code (and, for execution, a
count-only manifest) — never the patient's name or any identity detail (the audit service's
forbidden-key guard also rejects those keys).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound, ServiceUnavailable
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.enums import DeletionReasonCategory
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy import export as export_service
from hadp_api.modules.privacy import service as privacy_service
from hadp_api.modules.privacy.models import DeletionRequest
from hadp_api.modules.tenancy.models import Tenant
from hadp_api.security.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

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
    if patient is None:
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


@router.post("/deletion-requests/{request_id}/execute", response_model=DeletionRequestOut)
def execute_deletion_request(
    request_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_REQUEST_EXECUTE)),
) -> DeletionRequestOut:
    """Irreversibly erase the patient of an APPROVED request (gated tombstone).

    The DB work (anonymize the patient, hard-delete PII artifacts, withdraw consents, redact
    the append-only interpretation free text) runs in this request's single transaction. We
    commit it, then purge object storage AFTER commit — an S3 delete is not transactional, so
    it must not run before the DB is durable, and it is idempotent/re-runnable if it fails.
    """
    result = privacy_service.execute_request(
        ctx.db,
        tenant_id=ctx.tenant_id,
        request_id=request_id,
        executing_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="privacy.erasure_executed",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="deletion_request",
        target_id=result.request.id,
        correlation_id=ctx.correlation_id,
        # Count-only manifest — no identifiers or values.
        detail=dict(result.manifest),
    )
    # Build the response while the tenant-scoped transaction is still open (RLS context is
    # transaction-local, so a post-commit re-read would be unscoped/blocked).
    patient = _patient(ctx, result.request.patient_id)
    out = _out(result.request, patient)

    ctx.db.commit()

    # Post-commit: purge source-document objects. Idempotent; a failure is logged + audited on
    # its own transaction, never fatal (the DB erasure already committed).
    store = get_blob_store(get_settings())
    failures = 0
    for key in result.storage_keys:
        try:
            store.delete(key)
        except Exception as exc:  # noqa: BLE001 - purge must not resurrect a committed erasure
            failures += 1
            logger.error("erasure storage purge failed error=%s", type(exc).__name__)
    if failures:
        record_security_event(
            action="privacy.erasure_storage_incomplete",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
            detail={"failed_objects": failures},
        )
    return out


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


# --- Data export (GDPR Art. 15 / Art. 20) ---

EXPORT_AUDIT_ACTION = "privacy.export"


class DataExportOut(BaseModel):
    """One generated export, as its audit event recorded it (no content is kept)."""

    exported_at: datetime
    exported_by_user_id: uuid.UUID | None
    byte_size: int
    checksum_sha256: str
    observations: int
    computed_values: int
    consent_events: int
    # Stored files a reader imported into this record / shipped in the package / no longer
    # in storage / no longer matching their recorded checksum / stored but never imported.
    source_documents: int
    source_files: int
    source_files_missing: int
    source_files_changed: int
    source_documents_not_imported: int
    released_report_versions: int
    withdrawn_report_versions: int


@router.post(
    "/patients/{patient_id}/data-export",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}, "description": "The export package"}},
)
def export_patient_data(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_EXPORT)),
) -> Response:
    """Generate and download the patient's data package (a ZIP; see docs/product/DATA_EXPORT.md)."""
    check_rate_limit(
        action=EXPORT_AUDIT_ACTION,
        key=str(ctx.user.id),
        limit=5,
        window_seconds=600,
        correlation_id=ctx.correlation_id,
    )
    patient = _patient(ctx, patient_id)
    tenant = ctx.db.get(Tenant, ctx.tenant_id)
    if tenant is None:  # pragma: no cover - the tenant context was just resolved
        raise NotFound("tenant not found")
    try:
        package = export_service.build_patient_export(ctx.db, tenant=tenant, patient=patient)
    except (Conflict, ServiceUnavailable) as exc:
        # A refused export of a whole record is an attempt worth a trace. Recorded on its own
        # transaction (this request rolls back) with the refusal code only.
        record_security_event(
            action="privacy.export_refused",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
            detail={"code": exc.detail.split(":", 1)[0], "patient_id": str(patient_id)},
        )
        raise
    record_audit(
        ctx.db,
        action=EXPORT_AUDIT_ACTION,
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
        detail={
            **package.counts,
            "byte_size": len(package.data),
            "checksum_sha256": package.checksum_sha256,
            "format_version": export_service.FORMAT_VERSION,
        },
    )
    return Response(
        content=package.data,
        media_type="application/zip",
        headers={
            "content-disposition": f'attachment; filename="{package.filename}"',
            "x-checksum-sha256": package.checksum_sha256,
        },
    )


@router.get("/patients/{patient_id}/data-exports", response_model=list[DataExportOut])
def list_patient_data_exports(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PRIVACY_EXPORT)),
) -> list[DataExportOut]:
    """Exports generated for this patient so far, newest first (read from the audit trail)."""
    _patient(ctx, patient_id)
    events = ctx.db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == ctx.tenant_id,
            AuditEvent.action == EXPORT_AUDIT_ACTION,
            AuditEvent.target_id == patient_id,
        )
        .order_by(AuditEvent.created_at.desc())
    ).scalars()

    def count(event: AuditEvent, key: str) -> int:
        return int(event.detail.get(key, 0))

    return [
        DataExportOut(
            exported_at=event.created_at,
            exported_by_user_id=event.actor_user_id,
            byte_size=count(event, "byte_size"),
            checksum_sha256=str(event.detail.get("checksum_sha256", "")),
            observations=count(event, "observations"),
            computed_values=count(event, "computed_values"),
            consent_events=count(event, "consent_events"),
            source_documents=count(event, "source_documents"),
            source_files=count(event, "source_files"),
            source_files_missing=count(event, "source_files_missing"),
            source_files_changed=count(event, "source_files_changed"),
            source_documents_not_imported=count(event, "source_documents_not_imported"),
            released_report_versions=count(event, "released_report_versions"),
            withdrawn_report_versions=count(event, "withdrawn_report_versions"),
        )
        for event in events
    ]
