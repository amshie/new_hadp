"""Import pipeline service: turn input lab values into reviewed/published observations.

Implements the pipeline RECEIVED -> ... -> REVIEW_REQUIRED | READY -> PUBLISHED. Rows
that need review are NOT published until a human resolves them (CLAUDE.md). Provenance
(parser name/version, source locator) is preserved on every observation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hadp_api.modules.enums import ImportStatus, ReviewStatus, ValueType
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.imports.models import ImportJob, ImportRow, ReviewItem
from hadp_api.modules.kpi.service import resolve_kpi_code
from hadp_api.modules.observations.models import Observation


@dataclass
class ValueInput:
    original_name: str
    original_value: str
    original_unit: str | None
    observed_at: datetime
    observed_at_is_date_only: bool = False
    reference_low: str | None = None
    reference_high: str | None = None
    source_record_locator: str | None = None


@dataclass
class ImportResult:
    import_job_id: uuid.UUID
    observation_ids: list[uuid.UUID] = field(default_factory=list)
    review_item_ids: list[uuid.UUID] = field(default_factory=list)
    published_count: int = 0
    review_count: int = 0


def ingest_values(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    rows: list[ValueInput],
    parser_name: str,
    parser_version: str,
    created_by_user_id: uuid.UUID,
    source_document_id: uuid.UUID | None = None,
) -> ImportResult:
    job = ImportJob(
        tenant_id=tenant_id,
        patient_id=patient_id,
        source_document_id=source_document_id,
        status=ImportStatus.RECEIVED,
        parser_name=parser_name,
        parser_version=parser_version,
        created_by_user_id=created_by_user_id,
    )
    db.add(job)
    db.flush()

    result = ImportResult(import_job_id=job.id)
    now = datetime.now(UTC)

    for index, row in enumerate(rows):
        norm = normalize_mod.normalize(
            original_name=row.original_name,
            original_value=row.original_value,
            original_unit=row.original_unit,
            reference_low=row.reference_low,
            reference_high=row.reference_high,
        )
        needs_review = norm.needs_review
        review_status = ReviewStatus.PENDING if needs_review else ReviewStatus.PUBLISHED

        observation = Observation(
            tenant_id=tenant_id,
            patient_id=patient_id,
            source_document_id=source_document_id,
            source_record_locator=row.source_record_locator,
            original_name=row.original_name,
            original_value=row.original_value,
            original_unit=row.original_unit,
            reference_text=(
                f"{row.reference_low}-{row.reference_high} {row.original_unit or ''}".strip()
                if (row.reference_low or row.reference_high)
                else None
            ),
            metric_code=norm.metric_code,
            code_system=norm.code_system,
            kpi_code=resolve_kpi_code(db, row.original_name, norm.metric_code),
            mapping_confidence=norm.mapping_confidence,
            value_type=ValueType.NUMERIC,
            numeric_value=norm.normalized_value,
            normalized_value=norm.normalized_value,
            normalized_unit=norm.normalized_unit,
            reference_low=norm.reference_low,
            reference_high=norm.reference_high,
            normalization_version=norm.normalization_version,
            observed_at=row.observed_at,
            observed_at_is_date_only=row.observed_at_is_date_only,
            received_at=now,
            review_status=review_status,
        )
        db.add(observation)
        db.flush()
        result.observation_ids.append(observation.id)

        import_row = ImportRow(
            tenant_id=tenant_id,
            import_job_id=job.id,
            row_index=index,
            raw={
                "original_name": row.original_name,
                "original_value": row.original_value,
                "original_unit": row.original_unit,
                "observed_at": row.observed_at.isoformat(),
            },
            status=ImportStatus.REVIEW_REQUIRED if needs_review else ImportStatus.PUBLISHED,
        )
        db.add(import_row)
        db.flush()

        if needs_review:
            for reason in norm.review_reasons:
                item = ReviewItem(
                    tenant_id=tenant_id,
                    import_row_id=import_row.id,
                    observation_id=observation.id,
                    reason=reason,
                    detail={"row_index": index},
                    resolved=False,
                )
                db.add(item)
                db.flush()
                result.review_item_ids.append(item.id)
            result.review_count += 1
        else:
            result.published_count += 1

    job.status = ImportStatus.REVIEW_REQUIRED if result.review_count else ImportStatus.PUBLISHED
    db.flush()
    return result
