"""Ingestion routes: upload a source document and import lab values into observations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel, Field

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.errors import Conflict, ValidationFailed
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.documents.service import store_source_document
from hadp_api.modules.enums import ReviewDecision, ReviewStatus
from hadp_api.modules.imports import service as imports_service
from hadp_api.modules.imports.document_import import import_source_document
from hadp_api.modules.imports.service import ValueInput, ingest_values
from hadp_api.modules.patients import service as patients_service
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(tags=["imports"])


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    checksum_sha256: str
    created: bool


class ImportValueIn(BaseModel):
    original_name: str = Field(min_length=1, max_length=200)
    original_value: str = Field(min_length=1, max_length=120)
    original_unit: str | None = Field(default=None, max_length=60)
    observed_at: datetime
    observed_at_is_date_only: bool = False
    reference_low: str | None = None
    reference_high: str | None = None
    source_record_locator: str | None = Field(default=None, max_length=255)


class ImportRequest(BaseModel):
    source_document_id: uuid.UUID | None = None
    parser_name: str = "manual-entry"
    parser_version: str = "1"
    values: list[ImportValueIn] = Field(min_length=1)


class ImportResultOut(BaseModel):
    import_job_id: uuid.UUID
    published_count: int
    review_count: int
    # Values the patient already holds — recorded, not imported a second time. They have no
    # entry in `observation_ids`.
    duplicate_count: int
    observation_ids: list[uuid.UUID]
    review_item_ids: list[uuid.UUID]


@router.post("/patients/{patient_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    patient_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require(Action.DOCUMENT_UPLOAD)),
) -> DocumentOut:
    check_rate_limit(
        action="document.upload",
        key=str(ctx.user.id),
        limit=30,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    data = await file.read()
    document, created = store_source_document(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="document.upload",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="source_document",
        target_id=document.id,
        correlation_id=ctx.correlation_id,
        detail={"created": created, "byte_size": document.byte_size},
    )
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        checksum_sha256=document.checksum_sha256,
        created=created,
    )


def _observed_at(value: ImportValueIn) -> datetime:
    """A day-only value is stored as that calendar day (midnight UTC), whatever offset the
    client wrote it with — the day as written is the source's statement, not an instant."""
    if value.observed_at_is_date_only:
        day = value.observed_at.date()
        return datetime(day.year, day.month, day.day, tzinfo=UTC)
    if value.observed_at.tzinfo is None:
        return value.observed_at.replace(tzinfo=UTC)
    return value.observed_at


@router.post("/patients/{patient_id}/imports", response_model=ImportResultOut, status_code=201)
def run_import(
    patient_id: uuid.UUID,
    body: ImportRequest,
    ctx: TenantContext = Depends(require(Action.IMPORT_RUN)),
) -> ImportResultOut:
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    rows = [
        ValueInput(
            original_name=v.original_name,
            original_value=v.original_value,
            original_unit=v.original_unit,
            observed_at=_observed_at(v),
            observed_at_is_date_only=v.observed_at_is_date_only,
            reference_low=v.reference_low,
            reference_high=v.reference_high,
            source_record_locator=v.source_record_locator,
        )
        for v in body.values
    ]
    result = ingest_values(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        rows=rows,
        parser_name=body.parser_name,
        parser_version=body.parser_version,
        created_by_user_id=ctx.user.id,
        source_document_id=body.source_document_id,
    )
    record_audit(
        ctx.db,
        action="import.run",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="import_job",
        target_id=result.import_job_id,
        correlation_id=ctx.correlation_id,
        detail={
            "published": result.published_count,
            "review": result.review_count,
            "duplicates": result.duplicate_count,
        },
    )
    return ImportResultOut(
        import_job_id=result.import_job_id,
        published_count=result.published_count,
        review_count=result.review_count,
        duplicate_count=result.duplicate_count,
        observation_ids=result.observation_ids,
        review_item_ids=result.review_item_ids,
    )


class DocumentImportOut(BaseModel):
    import_job_id: uuid.UUID
    parser_name: str
    parser_version: str
    published_count: int
    review_count: int
    # Values the patient already holds — recorded, not imported a second time.
    duplicate_count: int
    not_imported_count: int
    created: bool


@router.post(
    "/patients/{patient_id}/documents/{document_id}/import",
    response_model=DocumentImportOut,
    status_code=201,
)
def import_document(
    patient_id: uuid.UUID,
    document_id: uuid.UUID,
    response: Response,
    ctx: TenantContext = Depends(require(Action.IMPORT_RUN)),
) -> DocumentImportOut:
    """Read a stored structured laboratory file (CSV or LDT) into the import pipeline.

    Idempotent per document: a repeat returns the first import (200) and writes nothing.
    """
    check_rate_limit(
        action="document.import",
        key=str(ctx.user.id),
        limit=30,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
    patient = patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    try:
        result = import_source_document(
            ctx.db,
            tenant_id=ctx.tenant_id,
            patient=patient,
            document_id=document_id,
            created_by_user_id=ctx.user.id,
        )
    except (ValidationFailed, Conflict) as exc:
        # A refused file (unreadable, another patient's) is an attempt worth a trace. Recorded
        # on its own transaction — this request rolls back — with the refusal code only.
        record_security_event(
            action="import.refused",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
            detail={
                "code": exc.detail.split(":", 1)[0],
                "source_document_id": str(document_id),
            },
        )
        raise
    if result.created:
        record_audit(
            ctx.db,
            action="import.run",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            target_type="import_job",
            target_id=result.import_job_id,
            correlation_id=ctx.correlation_id,
            detail={
                "published": result.published_count,
                "review": result.review_count,
                "duplicates": result.duplicate_count,
                "not_imported": result.not_imported_count,
                "parser": result.parser_name,
                "parser_version": result.parser_version,
            },
        )
    else:
        response.status_code = 200
    return DocumentImportOut(
        import_job_id=result.import_job_id,
        parser_name=result.parser_name,
        parser_version=result.parser_version,
        published_count=result.published_count,
        review_count=result.review_count,
        duplicate_count=result.duplicate_count,
        not_imported_count=result.not_imported_count,
        created=result.created,
    )


class HeldValueOut(BaseModel):
    """A value the patient already holds, as source representation."""

    observation_id: uuid.UUID
    original_name: str
    original_value: str
    original_unit: str | None
    observed_at: datetime
    observed_at_is_date_only: bool
    review_status: str
    # A published correction has replaced this value.
    superseded: bool


class ReviewItemOut(BaseModel):
    review_item_id: uuid.UUID
    observation_id: uuid.UUID
    patient_id: uuid.UUID
    patient_display_name: str
    patient_external_ref: str | None
    reason: str
    original_name: str
    original_value: str
    original_unit: str | None
    observed_at: datetime
    observed_at_is_date_only: bool
    created_at: datetime
    # The held value this one replaces once it is published (a source-marked correction).
    replaces: HeldValueOut | None
    # Reports whose current version cites the value that would be replaced.
    replaces_cited_in_report_count: int
    # Other values held for the same analyte and sampling time.
    related: list[HeldValueOut]


class ResolveReviewIn(BaseModel):
    decision: ReviewDecision


class ResolveReviewOut(BaseModel):
    review_item_id: uuid.UUID
    observation_id: uuid.UUID
    decision: str
    observation_review_status: str


@router.get("/review-items", response_model=list[ReviewItemOut])
def list_review_items(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> list[ReviewItemOut]:
    items = imports_service.list_open_review_items(ctx.db, ctx.tenant_id)
    record_audit(
        ctx.db,
        action="review_queue.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"open": len(items)},
    )
    return [ReviewItemOut(**item) for item in items]


@router.post("/review-items/{review_item_id}/resolve", response_model=ResolveReviewOut)
def resolve_review_item(
    review_item_id: uuid.UUID,
    body: ResolveReviewIn,
    ctx: TenantContext = Depends(require(Action.REVIEW_RESOLVE)),
) -> ResolveReviewOut:
    item, observation = imports_service.resolve_review_item(
        ctx.db,
        tenant_id=ctx.tenant_id,
        review_item_id=review_item_id,
        decision=body.decision,
        resolved_by_user_id=ctx.user.id,
    )
    detail: dict[str, str] = {"decision": body.decision.value, "reason": item.reason}
    if (
        observation.supersedes_observation_id is not None
        and observation.review_status == ReviewStatus.PUBLISHED
    ):
        # This decision made a laboratory correction take effect.
        detail["superseded_observation_id"] = str(observation.supersedes_observation_id)
    record_audit(
        ctx.db,
        action="review_item.resolved",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="review_item",
        target_id=item.id,
        correlation_id=ctx.correlation_id,
        detail=detail,
    )
    return ResolveReviewOut(
        review_item_id=item.id,
        observation_id=observation.id,
        decision=body.decision.value,
        observation_review_status=observation.review_status.value,
    )
