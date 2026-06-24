"""Ingestion routes: upload a source document and import lab values into observations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.documents.service import store_source_document
from hadp_api.modules.imports.service import ValueInput, ingest_values
from hadp_api.modules.patients import service as patients_service

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
    observation_ids: list[uuid.UUID]
    review_item_ids: list[uuid.UUID]


@router.post("/patients/{patient_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    patient_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require(Action.DOCUMENT_UPLOAD)),
) -> DocumentOut:
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
            observed_at=v.observed_at
            if v.observed_at.tzinfo
            else v.observed_at.replace(tzinfo=UTC),
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
        detail={"published": result.published_count, "review": result.review_count},
    )
    return ImportResultOut(
        import_job_id=result.import_job_id,
        published_count=result.published_count,
        review_count=result.review_count,
        observation_ids=result.observation_ids,
        review_item_ids=result.review_item_ids,
    )
