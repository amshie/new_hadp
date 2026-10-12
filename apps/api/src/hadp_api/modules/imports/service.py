"""Import pipeline service: turn input lab values into reviewed/published observations.

Implements the pipeline RECEIVED -> ... -> REVIEW_REQUIRED | READY -> PUBLISHED. Rows
that need review are NOT published until a human resolves them (CLAUDE.md). Provenance
(parser name/version, source locator) is preserved on every observation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.enums import ImportStatus, ReviewDecision, ReviewStatus, ValueType
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.imports.models import ImportJob, ImportRow, ReviewItem
from hadp_api.modules.kpi.service import resolve_kpi_code
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient


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
    # The source's own wording of the reference interval, when it gives one.
    reference_text: str | None = None
    # Reasons a reader found in the SOURCE (e.g. a non-final result) — the row is held for
    # review even when normalization alone would publish it.
    review_reasons: tuple[str, ...] = ()


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
    idempotency_key: str | None = None,
) -> ImportResult:
    job = ImportJob(
        tenant_id=tenant_id,
        patient_id=patient_id,
        source_document_id=source_document_id,
        status=ImportStatus.RECEIVED,
        parser_name=parser_name,
        parser_version=parser_version,
        idempotency_key=idempotency_key,
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
        review_reasons = [*norm.review_reasons, *row.review_reasons]
        needs_review = bool(review_reasons)
        review_status = ReviewStatus.PENDING if needs_review else ReviewStatus.PUBLISHED

        observation = Observation(
            tenant_id=tenant_id,
            patient_id=patient_id,
            source_document_id=source_document_id,
            source_record_locator=row.source_record_locator,
            original_name=row.original_name,
            original_value=row.original_value,
            original_unit=row.original_unit,
            reference_text=row.reference_text
            or (
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
            for reason in review_reasons:
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


def list_open_review_items(db: Session, tenant_id: uuid.UUID) -> list[dict[str, object]]:
    """Open review items with the observation context a reviewer needs (tenant-scoped).

    Returns source representation only (original name/value/unit + the closed reason) —
    review happens BEFORE normalization is trusted, so nothing normalized is presented
    as settled.
    """
    rows = db.execute(
        select(ReviewItem, Observation, Patient)
        .join(Observation, ReviewItem.observation_id == Observation.id)
        .join(Patient, Observation.patient_id == Patient.id)
        .where(
            ReviewItem.tenant_id == tenant_id,
            ReviewItem.resolved.is_(False),
        )
        .order_by(ReviewItem.created_at.asc())
    ).all()
    return [
        {
            "review_item_id": item.id,
            "observation_id": obs.id,
            "patient_id": obs.patient_id,
            "patient_display_name": patient.display_name,
            "patient_external_ref": patient.external_ref,
            "reason": item.reason,
            "original_name": obs.original_name,
            "original_value": obs.original_value,
            "original_unit": obs.original_unit,
            "observed_at": obs.observed_at,
            "observed_at_is_date_only": obs.observed_at_is_date_only,
            "created_at": item.created_at,
        }
        for item, obs, patient in rows
    ]


def resolve_review_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    review_item_id: uuid.UUID,
    decision: ReviewDecision,
    resolved_by_user_id: uuid.UUID,
) -> tuple[ReviewItem, Observation]:
    """Resolve one review item with an attributable human decision (clinician).

    REJECT is fail-closed and immediate: one refused item rejects the observation.
    PUBLISH takes effect only when it resolves the LAST open item for the observation —
    an observation with any other open item stays PENDING (nothing publishes while a
    conflict is unresolved). Resolution never mutates the observation's source
    representation; only `review_status` transitions.
    """
    item = db.execute(
        select(ReviewItem).where(
            ReviewItem.id == review_item_id,
            ReviewItem.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFound("review item not found")
    if item.resolved:
        raise Conflict("review item is already resolved")
    if item.observation_id is None:
        raise Conflict("review item has no observation to resolve")
    observation = db.get(Observation, item.observation_id)
    if observation is None or observation.tenant_id != tenant_id:
        raise NotFound("review item not found")
    if observation.review_status != ReviewStatus.PENDING:
        raise Conflict("observation is no longer pending review")

    item.resolved = True
    item.resolved_by_user_id = resolved_by_user_id
    item.resolved_at = datetime.now(UTC)
    db.flush()

    if decision == ReviewDecision.REJECT:
        observation.review_status = ReviewStatus.REJECTED
    else:
        open_items = db.execute(
            select(ReviewItem.id).where(
                ReviewItem.observation_id == observation.id,
                ReviewItem.resolved.is_(False),
            )
        ).first()
        if open_items is None:
            observation.review_status = ReviewStatus.PUBLISHED
    db.flush()
    return item, observation
