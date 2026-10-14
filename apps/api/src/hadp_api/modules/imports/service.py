"""Import pipeline service: turn input lab values into reviewed/published observations.

Implements the pipeline RECEIVED -> ... -> REVIEW_REQUIRED | READY -> PUBLISHED. Rows
that need review are NOT published until a human resolves them (CLAUDE.md). Provenance
(parser name/version, source locator) is preserved on every observation.

Every incoming value is matched against what the patient already holds (`matching.py`): a
value nothing distinguishes from a held one is not imported twice, a source-marked correction
proposes to replace the one value it can correct, and any other value for an occupied analyte
and sampling time is held for review.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.enums import (
    ImportStatus,
    KpiMeasurementClass,
    ReviewDecision,
    ReviewStatus,
    ValueType,
)
from hadp_api.modules.imports import matching
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.imports.models import ImportJob, ImportRow, ReviewItem
from hadp_api.modules.kpi.service import load_terminology
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports import service as reports_service

logger = logging.getLogger(__name__)


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
    # Input values the patient already holds: recorded, not imported a second time.
    duplicate_count: int = 0


def source_reference_text(
    text: str | None, low: str | None, high: str | None, unit: str | None
) -> str | None:
    """The reference as the source gave it, for the reader of the value.

    The source's own wording when it wrote one. Otherwise its bounds, as written, with the
    value's unit — and only the bounds it gave: a single bound is named as the lower or upper
    bound, and nothing is said about the other (the source may give a one-sided interval). No
    bound and no wording: no reference text.
    """
    if text:
        return text
    low = (low or "").strip()
    high = (high or "").strip()
    if low and high:
        bounds = f"{low}-{high}"
    elif high:
        bounds = f"obere Grenze {high}"
    elif low:
        bounds = f"untere Grenze {low}"
    else:
        return None
    return f"{bounds} {(unit or '').strip()}".strip()


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
    matching.lock_patient_record(db, patient_id)
    record = matching.PatientRecord(
        db,
        tenant_id=tenant_id,
        patient_id=patient_id,
        zone=ZoneInfo(get_settings().lab_local_timezone),
    )

    terminology = load_terminology(db)
    unconfirmed = normalize_mod.unconfirmed_names(terminology)
    if unconfirmed:
        # A catalog that was never seeded, or that no longer describes these names as the
        # import does: their values wait for review instead of being normalized. Nothing else
        # would show it — the queue only says "not mapped". (The names are the import's own
        # fixed list, not source text.)
        logger.error(
            "KPI catalog does not confirm %d of the import's %d automatic names (%s); "
            "their values are held for review",
            len(unconfirmed),
            len(normalize_mod.automatic_names()),
            ", ".join(unconfirmed),
        )

    for index, row in enumerate(rows):
        norm = normalize_mod.normalize(
            terminology=terminology,
            original_name=row.original_name,
            original_value=row.original_value,
            original_unit=row.original_unit,
            reference_low=row.reference_low,
            reference_high=row.reference_high,
        )

        observation = Observation(
            tenant_id=tenant_id,
            patient_id=patient_id,
            source_document_id=source_document_id,
            source_record_locator=row.source_record_locator,
            original_name=row.original_name,
            original_value=row.original_value,
            original_unit=row.original_unit,
            reference_text=source_reference_text(
                row.reference_text, row.reference_low, row.reference_high, row.original_unit
            ),
            metric_code=norm.metric_code,
            code_system=norm.code_system,
            kpi_code=norm.kpi_code,
            mapping_confidence=norm.mapping_confidence,
            value_type=ValueType.NUMERIC,
            numeric_value=norm.numeric_value,
            normalized_value=norm.normalized_value,
            normalized_unit=norm.normalized_unit,
            reference_low=norm.reference_low,
            reference_high=norm.reference_high,
            normalization_version=norm.normalization_version,
            observed_at=row.observed_at,
            observed_at_is_date_only=row.observed_at_is_date_only,
            received_at=now,
            review_status=ReviewStatus.PENDING,
        )
        raw: dict[str, Any] = {
            "original_name": row.original_name,
            "original_value": row.original_value,
            "original_unit": row.original_unit,
            "observed_at": row.observed_at.isoformat(),
        }
        match = record.match(observation, row.review_reasons)
        if match.duplicate_of is not None:
            # The patient already holds exactly this value: record where it was seen again
            # and which observation it repeats, and create nothing.
            db.add(
                ImportRow(
                    tenant_id=tenant_id,
                    import_job_id=job.id,
                    row_index=index,
                    raw={
                        **raw,
                        "source_record_locator": row.source_record_locator,
                        "not_imported_reason": matching.DUPLICATE_VALUE,
                        "duplicate_of_observation_id": str(match.duplicate_of.id),
                    },
                    status=ImportStatus.REJECTED,
                )
            )
            result.duplicate_count += 1
            continue

        review_reasons = [*norm.review_reasons, *row.review_reasons, *match.review_reasons]
        needs_review = bool(review_reasons)
        observation.review_status = ReviewStatus.PENDING if needs_review else ReviewStatus.PUBLISHED
        if match.supersedes is not None:
            # A proposal only: the source's correction mark is itself a review reason, so the
            # replacement takes effect when a human publishes this value — never before.
            observation.supersedes_observation_id = match.supersedes.id
        db.add(observation)
        db.flush()
        record.add(observation, review_reasons)
        result.observation_ids.append(observation.id)

        import_row = ImportRow(
            tenant_id=tenant_id,
            import_job_id=job.id,
            row_index=index,
            raw=raw,
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

    if result.review_count:
        job.status = ImportStatus.REVIEW_REQUIRED
    elif result.published_count:
        job.status = ImportStatus.PUBLISHED
    else:
        # Nothing was carried (every value is already held, or there were none): the job must
        # not read as published.
        job.status = ImportStatus.REJECTED
    db.flush()
    return result


def _held_value(observation: Observation, replaced: set[uuid.UUID]) -> dict[str, object]:
    """A value the patient already holds, as source representation (context for a reviewer)."""
    return {
        "observation_id": observation.id,
        "original_name": observation.original_name,
        "original_value": observation.original_value,
        "original_unit": observation.original_unit,
        "observed_at": observation.observed_at,
        "observed_at_is_date_only": observation.observed_at_is_date_only,
        "review_status": observation.review_status.value,
        "superseded": observation.id in replaced,
    }


def list_open_review_items(db: Session, tenant_id: uuid.UUID) -> list[dict[str, object]]:
    """Open review items with the observation context a reviewer needs (tenant-scoped).

    Returns source representation only (original name/value/unit + the closed reason) —
    review happens BEFORE normalization is trusted, so nothing normalized is presented
    as settled. Every item also names the other values the patient holds for the same analyte
    and sampling time — read at listing time, not as they were at import — so a decision about
    a repeat or a correction is never made blind.
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

    patient_ids = {obs.patient_id for _item, obs, _patient in rows}
    held: dict[uuid.UUID, list[Observation]] = {}
    replaced: set[uuid.UUID] = set()
    if patient_ids:
        for other in db.execute(
            select(Observation)
            .where(Observation.tenant_id == tenant_id, Observation.patient_id.in_(patient_ids))
            .order_by(Observation.received_at, Observation.id)
        ).scalars():
            if other.source_category != KpiMeasurementClass.DERIVED:
                held.setdefault(other.patient_id, []).append(other)
        for patient_id in patient_ids:
            replaced.update(obs_service.superseded_by(db, patient_id))
    zone = ZoneInfo(get_settings().lab_local_timezone)

    out: list[dict[str, object]] = []
    for item, obs, patient in rows:
        # Context is read per patient: it cannot cross patients. The value a correction would
        # replace is the one the decision will act on (the stored link), whatever it matches.
        others = [other for other in held.get(obs.patient_id, []) if other.id != obs.id]
        target = next((o for o in others if o.id == obs.supersedes_observation_id), None)
        same = [o for o in others if matching.same_measurement(o, obs, zone)]
        out.append(
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
                # What publishing this value puts into effect beside it: the reference bounds
                # the platform holds, in the unit it holds the value in.
                "reference_low": obs_service.plain(obs.reference_low),
                "reference_high": obs_service.plain(obs.reference_high),
                "reference_unit": obs_service.held_value(obs)[1],
                "reference_converted": normalize_mod.unit_was_converted(
                    obs.original_unit, obs.normalized_unit
                ),
                "observed_at": obs.observed_at,
                "observed_at_is_date_only": obs.observed_at_is_date_only,
                "created_at": item.created_at,
                "replaces": _held_value(target, replaced) if target is not None else None,
                "replaces_cited_in_report_count": (
                    reports_service.count_reports_citing(db, tenant_id, target.id)
                    if target is not None
                    else 0
                ),
                "related": [_held_value(o, replaced) for o in same if o is not target],
            }
        )
    return out


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

    Publishing a value the source sent as a correction is what makes the replacement take
    effect: the earlier value stays as it is and is from then on read as replaced. A rejected
    correction replaces nothing.
    """
    item = db.execute(
        select(ReviewItem).where(
            ReviewItem.id == review_item_id,
            ReviewItem.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFound("review item not found")
    if item.observation_id is None:
        raise Conflict("review item has no observation to resolve")
    patient_id = db.execute(
        select(Observation.patient_id).where(
            Observation.id == item.observation_id, Observation.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if patient_id is None:
        raise NotFound("review item not found")
    # Decisions and imports for one patient take turns, under the one lock an import takes
    # too (no second lock, so no lock order to get wrong): two reviewers resolving two items
    # of one value must not each see the other's item as still open, and a correction must
    # not be published while an import is matching against the value it replaces.
    matching.lock_patient_record(db, patient_id)
    db.refresh(item)
    observation = db.get(Observation, item.observation_id)
    if observation is None:
        raise NotFound("review item not found")
    if item.resolved:
        raise Conflict("review item is already resolved")
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
            target_id = observation.supersedes_observation_id
            if target_id is not None and target_id in obs_service.superseded_by(
                db, observation.patient_id
            ):
                # Another published correction already replaced that value: two values must
                # not both stand as "the" correction of one.
                raise Conflict(
                    "supersession_conflict: the value this one corrects has already been replaced"
                )
            observation.review_status = ReviewStatus.PUBLISHED
    db.flush()
    return item, observation
