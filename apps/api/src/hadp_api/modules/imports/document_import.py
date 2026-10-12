"""Import a stored source document through a structured reader (ingestion tier 1).

The original file is already stored (documents service). This reads it back, lets the matching
reader turn it into rows, and hands those to the same `ingest_values` pipeline as manual entry —
so normalization, the review queue and provenance behave identically. A document is imported at
most once: a repeat returns the first import instead of duplicating its observations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound, ValidationFailed
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import ImportStatus
from hadp_api.modules.imports.models import ImportJob, ImportRow
from hadp_api.modules.imports.parsers import SourceParseError, parse_source_document
from hadp_api.modules.imports.service import ValueInput, ingest_values
from hadp_api.modules.patients.models import Patient


@dataclass
class DocumentImportResult:
    import_job_id: uuid.UUID
    parser_name: str
    parser_version: str
    published_count: int
    review_count: int
    # Results the file contains but the pipeline cannot carry (text results, results still to
    # come). Each is recorded as a rejected import row with its locator and reason.
    not_imported_count: int
    created: bool


def _first_import(db: Session, job: ImportJob) -> DocumentImportResult:
    """The outcome of the import that already consumed this document (as it was imported)."""
    counts = dict(
        db.execute(
            select(ImportRow.status, func.count())
            .where(ImportRow.import_job_id == job.id)
            .group_by(ImportRow.status)
        )
        .tuples()
        .all()
    )
    return DocumentImportResult(
        import_job_id=job.id,
        parser_name=job.parser_name,
        parser_version=job.parser_version,
        published_count=counts.get(ImportStatus.PUBLISHED, 0),
        review_count=counts.get(ImportStatus.REVIEW_REQUIRED, 0),
        not_imported_count=counts.get(ImportStatus.REJECTED, 0),
        created=False,
    )


def import_source_document(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient: Patient,
    document_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
) -> DocumentImportResult:
    # The row lock serializes concurrent imports of one document: the second caller waits and
    # then finds the first import below. The document must belong to THIS patient.
    document = db.execute(
        select(SourceDocument)
        .where(
            SourceDocument.id == document_id,
            SourceDocument.tenant_id == tenant_id,
            SourceDocument.patient_id == patient.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if document is None:
        raise NotFound("source document not found")

    idempotency_key = f"document:{document.id}"
    existing = db.execute(
        select(ImportJob).where(
            ImportJob.tenant_id == tenant_id,
            ImportJob.idempotency_key == idempotency_key,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _first_import(db, existing)

    settings = get_settings()
    data = get_blob_store(settings).get(document.storage_key)
    try:
        parsed = parse_source_document(data, zone=ZoneInfo(settings.lab_local_timezone))
    except SourceParseError as exc:
        # Fail-closed: a file that cannot be read as a whole imports nothing.
        raise ValidationFailed(f"{exc.code}: {exc.detail}") from exc

    # A file that names a different date of birth is another person's report.
    if (
        parsed.patient_date_of_birth is not None
        and patient.date_of_birth is not None
        and parsed.patient_date_of_birth != patient.date_of_birth
    ):
        raise Conflict("source document does not match this patient")

    result = ingest_values(
        db,
        tenant_id=tenant_id,
        patient_id=patient.id,
        rows=[
            ValueInput(
                original_name=v.original_name,
                original_value=v.original_value,
                original_unit=v.original_unit,
                observed_at=v.observed_at,
                observed_at_is_date_only=v.observed_at_is_date_only,
                reference_low=v.reference_low,
                reference_high=v.reference_high,
                source_record_locator=v.source_record_locator,
                reference_text=v.reference_text,
                review_reasons=v.review_reasons,
            )
            for v in parsed.values
        ],
        parser_name=parsed.parser_name,
        parser_version=parsed.parser_version,
        created_by_user_id=created_by_user_id,
        source_document_id=document.id,
        idempotency_key=idempotency_key,
    )
    for offset, skipped in enumerate(parsed.not_imported):
        db.add(
            ImportRow(
                tenant_id=tenant_id,
                import_job_id=result.import_job_id,
                row_index=len(parsed.values) + offset,
                raw={
                    "source_record_locator": skipped.source_record_locator,
                    "not_imported_reason": skipped.reason,
                },
                status=ImportStatus.REJECTED,
            )
        )
    if not parsed.values:
        # Nothing in the file could be carried: the job must not read as published.
        job = db.get(ImportJob, result.import_job_id)
        if job is not None:
            job.status = ImportStatus.REJECTED
    db.flush()
    return DocumentImportResult(
        import_job_id=result.import_job_id,
        parser_name=parsed.parser_name,
        parser_version=parsed.parser_version,
        published_count=result.published_count,
        review_count=result.review_count,
        not_imported_count=len(parsed.not_imported),
        created=True,
    )
