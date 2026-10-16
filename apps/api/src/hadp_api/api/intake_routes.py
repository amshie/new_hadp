"""Lab intake agent routes: have a PDF read into proposals, see them beside the page, decide.

The agent itself writes through its MCP tool, not through HTTP. These routes are the HUMAN side:
`intake.propose` starts the configured provider over a stored document (care staff, like an
import); `intake.read` shows a batch and the page region each value came from; `intake.decide`
confirms, corrects or rejects — a clinician's step, and the only path by which a proposed value
becomes an observation.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound, ValidationFailed
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.documents.pdf_text import PdfUnreadable, read_pages
from hadp_api.modules.enums import IntakeDecisionKind, IntakeRejectionReason, PendingValueStatus
from hadp_api.modules.intake import decisions as decisions_service
from hadp_api.modules.intake import service as intake_service
from hadp_api.modules.intake.providers import get_provider
from hadp_api.modules.patients import service as patients_service
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(tags=["intake"])


class ProposeOut(BaseModel):
    batch_id: uuid.UUID
    extraction_provider: str
    value_count: int
    green: int
    yellow: int
    red: int


class IntakeBatchSummaryOut(BaseModel):
    batch_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    created_at: datetime
    extraction_provider: str
    model_id: str
    value_count: int
    green: int
    yellow: int
    red: int
    open_count: int


class CorrectedValueOut(BaseModel):
    analyte_text: str
    value_text: str
    unit_text: str | None
    observed_at: str | None
    observed_at_is_date_only: bool
    reference_low: str | None
    reference_high: str | None
    reference_text: str | None


class PendingValueOut(BaseModel):
    pending_value_id: uuid.UUID
    row_index: int
    analyte_text: str
    value_text: str
    unit_text: str | None
    observed_at: datetime | None
    observed_at_is_date_only: bool
    reference_low: str | None
    reference_high: str | None
    reference_text: str | None
    page: int
    has_region: bool
    confidence: Decimal
    kpi_code: str | None
    canonical_unit: str | None
    normalized_value: Decimal | None
    status: PendingValueStatus
    reasons: list[str]
    decision: IntakeDecisionKind | None
    decided_at: datetime | None
    observation_id: uuid.UUID | None
    rejection_reason: IntakeRejectionReason | None
    corrected_to: CorrectedValueOut | None


class IntakeBatchOut(BaseModel):
    batch_id: uuid.UUID
    patient_id: uuid.UUID
    patient_display_name: str
    document_id: uuid.UUID
    filename: str
    created_at: datetime
    extraction_provider: str
    model_id: str
    prompt_version: str
    page_count: int
    proposed_patient_date_of_birth: date | None
    proposed_issue_date: date | None
    batch_reasons: list[str]
    values: list[PendingValueOut]
    open_count: int


class CorrectionIn(BaseModel):
    analyte_text: str | None = Field(default=None, min_length=1, max_length=200)
    value_text: str | None = Field(default=None, min_length=1, max_length=120)
    unit_text: str | None = Field(default=None, max_length=60)
    observed_at: datetime | None = None
    observed_at_is_date_only: bool | None = None
    reference_low: str | None = Field(default=None, max_length=60)
    reference_high: str | None = Field(default=None, max_length=60)
    reference_text: str | None = Field(default=None, max_length=200)
    clear_unit: bool = False
    clear_reference: bool = False


class DecisionIn(BaseModel):
    pending_value_id: uuid.UUID
    decision: IntakeDecisionKind
    correction: CorrectionIn | None = None
    rejection_reason: IntakeRejectionReason | None = None
    review_seconds: int | None = Field(default=None, ge=0, le=86400)
    screen_seconds: int | None = Field(default=None, ge=0, le=86400)


class DecisionOut(BaseModel):
    decision_id: uuid.UUID
    pending_value_id: uuid.UUID
    decision: IntakeDecisionKind
    observation_id: uuid.UUID | None


class ConfirmGreenIn(BaseModel):
    screen_seconds: int | None = Field(default=None, ge=0, le=86400)


class ConfirmGreenOut(BaseModel):
    confirmed: int
    observation_ids: list[uuid.UUID]


@router.post(
    "/patients/{patient_id}/documents/{document_id}/intake",
    response_model=ProposeOut,
    status_code=201,
)
def propose_from_document(
    patient_id: uuid.UUID,
    document_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INTAKE_PROPOSE)),
) -> ProposeOut:
    """Run the configured extraction provider over a stored PDF of this patient. The provider
    proposes; the checks decide the status; nothing is published."""
    check_rate_limit(
        action="intake.propose",
        key=str(ctx.user.id),
        limit=30,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    document = ctx.db.execute(
        select(SourceDocument).where(
            SourceDocument.id == document_id,
            SourceDocument.tenant_id == ctx.tenant_id,
            SourceDocument.patient_id == patient_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFound("source document not found")
    settings = get_settings()
    store = get_blob_store(settings)
    if not store.exists(document.storage_key):
        raise Conflict("document_unavailable: the stored source document cannot be read")
    data = store.get(document.storage_key)
    try:
        pages = read_pages(data)
    except PdfUnreadable as exc:
        raise ValidationFailed(f"document_unreadable: {exc.detail}") from exc
    provider = get_provider(settings.intake_provider)
    proposal = provider.extract(data, pages)
    result = intake_service.create_pending_batch(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        document_id=document.id,
        proposal=proposal,
        created_by_user_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return ProposeOut(
        batch_id=result.batch_id,
        extraction_provider=provider.name,
        value_count=len(result.value_ids),
        green=result.green,
        yellow=result.yellow,
        red=result.red,
    )


@router.get("/patients/{patient_id}/intake-batches", response_model=list[IntakeBatchSummaryOut])
def list_intake_batches(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INTAKE_READ)),
) -> list[IntakeBatchSummaryOut]:
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    rows = decisions_service.list_batches(ctx.db, tenant_id=ctx.tenant_id, patient_id=patient_id)
    # Filed under no target: what a search by record finds is a fixed list the audit page
    # names (tests/test_audit_read.py); the record is in the detail.
    record_audit(
        ctx.db,
        action="intake.batches_list",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"patient_id": str(patient_id), "count": len(rows)},
    )
    return [IntakeBatchSummaryOut(**row) for row in rows]


@router.get("/intake/batches/{batch_id}", response_model=IntakeBatchOut)
def read_intake_batch(
    batch_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INTAKE_READ)),
) -> IntakeBatchOut:
    view = decisions_service.batch_view(ctx.db, tenant_id=ctx.tenant_id, batch_id=batch_id)
    record_audit(
        ctx.db,
        action="intake.batch_read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="intake_batch",
        target_id=batch_id,
        correlation_id=ctx.correlation_id,
        detail={"open_count": view["open_count"], "value_count": len(view["values"])},
    )
    return IntakeBatchOut(**view)


@router.get("/intake/values/{pending_value_id}/region", response_class=Response)
def read_value_region(
    pending_value_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.INTAKE_READ)),
) -> Response:
    """The page region a proposed value came from, as PNG: the document's own text and nothing
    the platform added. A read of health data, recorded like the batch itself."""
    png = decisions_service.region_png(
        ctx.db, tenant_id=ctx.tenant_id, pending_value_id=pending_value_id
    )
    record_audit(
        ctx.db,
        action="intake.region_read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="pending_value",
        target_id=pending_value_id,
        correlation_id=ctx.correlation_id,
        detail={"bytes": len(png)},
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"cache-control": "private, no-store"},
    )


@router.post("/intake/batches/{batch_id}/decisions", response_model=DecisionOut, status_code=201)
def decide_value(
    batch_id: uuid.UUID,
    body: DecisionIn,
    ctx: TenantContext = Depends(require(Action.INTAKE_DECIDE)),
) -> DecisionOut:
    # The value must be of THIS batch (the address says which batch is being worked on).
    view = decisions_service.batch_view(ctx.db, tenant_id=ctx.tenant_id, batch_id=batch_id)
    if body.pending_value_id not in {v["pending_value_id"] for v in view["values"]}:
        raise NotFound("pending value not found")
    correction = (
        decisions_service.CorrectionIn(**body.correction.model_dump())
        if body.correction is not None
        else None
    )
    row = decisions_service.decide(
        ctx.db,
        tenant_id=ctx.tenant_id,
        pending_value_id=body.pending_value_id,
        decision=body.decision,
        decided_by_user_id=ctx.user.id,
        correction=correction,
        rejection_reason=body.rejection_reason,
        review_seconds=body.review_seconds,
        screen_seconds=body.screen_seconds,
        correlation_id=ctx.correlation_id,
    )
    return DecisionOut(
        decision_id=row.id,
        pending_value_id=row.pending_value_id,
        decision=row.decision,
        observation_id=row.observation_id,
    )


@router.post("/intake/batches/{batch_id}/confirm-green", response_model=ConfirmGreenOut)
def confirm_green_values(
    batch_id: uuid.UUID,
    body: ConfirmGreenIn,
    ctx: TenantContext = Depends(require(Action.INTAKE_DECIDE)),
) -> ConfirmGreenOut:
    rows = decisions_service.confirm_green(
        ctx.db,
        tenant_id=ctx.tenant_id,
        batch_id=batch_id,
        decided_by_user_id=ctx.user.id,
        screen_seconds=body.screen_seconds,
        correlation_id=ctx.correlation_id,
    )
    return ConfirmGreenOut(
        confirmed=len(rows),
        observation_ids=[r.observation_id for r in rows if r.observation_id is not None],
    )
