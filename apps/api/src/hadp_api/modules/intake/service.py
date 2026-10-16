"""Lab intake agent — the ONE write: a batch of pending values.

`create_pending_batch` validates the proposal at the boundary (schema), reads the stored
document's page texts itself (never the agent's copy), runs the deterministic checks with the
catalog, the signed bounds and this patient's published record, and writes the batch and its
values with the status the checks computed. It writes no observation. There is no function in
this module — or anywhere the agent can reach — that moves a pending value into the record;
that is a human's step through the API, in a later slice.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound, ValidationFailed
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.documents.pdf_text import PdfUnreadable
from hadp_api.modules.enums import PendingValueStatus
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.intake import checks
from hadp_api.modules.intake.bounds_data import BOUNDS_VERSION, SIGNED_BOUNDS
from hadp_api.modules.intake.models import IntakeBatch, KpiPlausibilityBound, PendingValue
from hadp_api.modules.intake.pages import OcrUnavailable, PageSet, load_pages
from hadp_api.modules.intake.schemas import ProposedBatchIn
from hadp_api.modules.kpi.models import KpiCatalog
from hadp_api.modules.kpi.service import load_terminology
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.sampling import sampling_day
from hadp_api.modules.patients.models import Patient

# --- Signed bounds (global reference data) -----------------------------------------------------


def seed_plausibility_bounds(db: Session) -> int:
    """Insert the signed bounds of `bounds_data.py` that are not in the table yet. Idempotent.
    A bound whose unit is not the KPI's canonical unit, or whose KPI is not in the catalog, is
    a seed failure — never a row."""
    inserted = 0
    for kpi_code, unit, low, high, delta, source, signed_by, signed_at in SIGNED_BOUNDS:
        if db.get(KpiPlausibilityBound, kpi_code) is not None:
            continue
        kpi = db.get(KpiCatalog, kpi_code)
        if kpi is None:
            raise ValueError(f"plausibility bound for unknown KPI {kpi_code!r}")
        if kpi.canonical_unit_ucum != unit:
            raise ValueError(
                f"plausibility bound for {kpi_code!r} is in {unit!r}, "
                f"the catalog holds it in {kpi.canonical_unit_ucum!r}"
            )
        db.add(
            KpiPlausibilityBound(
                kpi_code=kpi_code,
                unit=unit,
                hard_low=Decimal(low) if low is not None else None,
                hard_high=Decimal(high) if high is not None else None,
                delta_max_relative=Decimal(delta) if delta is not None else None,
                source=source,
                signed_by=signed_by,
                signed_at=datetime.fromisoformat(signed_at).replace(tzinfo=UTC),
                bounds_version=BOUNDS_VERSION,
            )
        )
        inserted += 1
    db.flush()
    return inserted


class _DbBounds:
    def __init__(self, db: Session) -> None:
        self._db = db

    def for_kpi(self, kpi_code: str) -> checks.PlausibilityBound | None:
        row = self._db.get(KpiPlausibilityBound, kpi_code)
        if row is None:
            return None
        return checks.PlausibilityBound(
            unit=row.unit,
            hard_low=row.hard_low,
            hard_high=row.hard_high,
            delta_max_relative=row.delta_max_relative,
        )


# --- This patient's published record, as the checks may see it -----------------------------------


@dataclass
class _DbRecord:
    """Published, standing source values of ONE patient (never derived, never replaced)."""

    _date_of_birth: date | None
    _published: list[Observation]
    _zone: ZoneInfo

    @property
    def date_of_birth(self) -> date | None:
        return self._date_of_birth

    def last_published(self, kpi_code: str) -> checks.PriorValue | None:
        latest: Observation | None = None
        for obs in self._published:
            if obs.kpi_code == kpi_code and (
                latest is None or obs.observed_at >= latest.observed_at
            ):
                latest = obs
        if latest is None:
            return None
        value, unit = obs_service.held_value(latest)
        if value is None or unit is None:
            return None
        return checks.PriorValue(
            value=value, unit=unit, observed_at=latest.observed_at, observation_id=latest.id
        )

    def is_published(
        self,
        *,
        kpi_code: str | None,
        analyte_key: str,
        day: date | None,
        value_text: str,
        unit_text: str | None,
    ) -> bool:
        for obs in self._published:
            same_analyte = (kpi_code is not None and obs.kpi_code == kpi_code) or (
                checks.analyte_key(obs.original_name) == analyte_key
            )
            if not same_analyte:
                continue
            if day is None or sampling_day(obs, self._zone) != day:
                continue
            if " ".join(obs.original_value.split()) != value_text:
                continue
            if normalize_mod.canonical_unit_spelling(obs.original_unit) != unit_text:
                continue
            return True
        return False


def record_view(db: Session, patient: Patient) -> _DbRecord:
    """This patient's published, standing source values, as the checks and the agent's
    read tool may see them."""
    standing = obs_service.not_standing(db, patient.id)
    published = [
        o
        for o in obs_service.list_published(db, patient.id)
        if o.id not in standing and o.source_category != obs_service.KpiMeasurementClass.DERIVED
    ]
    return _DbRecord(patient.date_of_birth, published, ZoneInfo(get_settings().lab_local_timezone))


# --- The write ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchResult:
    batch_id: uuid.UUID
    value_ids: list[uuid.UUID]
    green: int
    yellow: int
    red: int


def create_pending_batch(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    document_id: uuid.UUID,
    proposal: ProposedBatchIn,
    created_by_user_id: uuid.UUID | None,
    correlation_id: str | None = None,
    today: date | None = None,
    shadow: bool = False,
) -> BatchResult:
    """Check and record what a model proposed from THIS patient's stored document.

    `shadow`: the batch is for comparison only (shadow mode) — it never reaches the
    confirmation screen and cannot be decided.

    Refuses (nothing written): a document that is not this patient's in this clinic, a stored
    file that is not a readable PDF, a proposal that does not fit the schema. Never refuses a
    proposal for what the checks find — red is recorded, not dropped: a human must see it.
    """
    patient = db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if patient is None:
        raise NotFound("patient not found")
    document = db.execute(
        select(SourceDocument).where(
            SourceDocument.id == document_id,
            SourceDocument.tenant_id == tenant_id,
            SourceDocument.patient_id == patient_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFound("source document not found")

    store = get_blob_store(get_settings())
    if not store.exists(document.storage_key):
        raise Conflict("document_unavailable: the stored source document cannot be read")
    try:
        pages: PageSet = load_pages(store.get(document.storage_key), get_settings())
    except PdfUnreadable as exc:
        raise ValidationFailed(f"document_unreadable: {exc.detail}") from exc
    except OcrUnavailable as exc:
        raise Conflict(f"ocr_unavailable: {exc.detail}") from exc

    batch_in = checks.ProposedBatch(
        patient_date_of_birth=proposal.patient_date_of_birth,
        issue_date=proposal.issue_date,
        values=tuple(
            checks.ProposedValue(
                analyte_text=v.analyte_text,
                value_text=v.value_text,
                unit_text=v.unit_text,
                observed_at=_observed_at(v.observed_at, v.observed_at_is_date_only),
                observed_at_is_date_only=v.observed_at_is_date_only,
                page=v.page,
                confidence=v.confidence,
                reference_low=v.reference_low,
                reference_high=v.reference_high,
                reference_text=v.reference_text,
                bbox=v.bbox,
            )
            for v in proposal.values
        ),
    )
    checked = checks.run_checks(
        batch_in,
        terminology=load_terminology(db),
        bounds=_DbBounds(db),
        record=record_view(db, patient),
        pages=pages,
        today=today or datetime.now(UTC).date(),
    )

    batch = IntakeBatch(
        tenant_id=tenant_id,
        patient_id=patient_id,
        source_document_id=document.id,
        created_by_user_id=created_by_user_id,
        extraction_provider=proposal.extraction_provider,
        model_id=proposal.model_id,
        prompt_version=proposal.prompt_version,
        page_count=pages.page_count,
        proposed_patient_date_of_birth=proposal.patient_date_of_birth,
        proposed_issue_date=proposal.issue_date,
        checks=[{"version": checks.CHECKS_VERSION}, *(c.as_dict() for c in checked.checks)],
        value_count=len(checked.values),
        page_sources=list(pages.sources),
        source_lab=(" ".join(proposal.source_lab.split())[:200] if proposal.source_lab else None),
        shadow=shadow,
    )
    db.add(batch)
    db.flush()

    counts = dict.fromkeys(PendingValueStatus, 0)
    value_ids: list[uuid.UUID] = []
    for index, value in enumerate(checked.values):
        p = value.proposal
        row = PendingValue(
            tenant_id=tenant_id,
            patient_id=patient_id,
            batch_id=batch.id,
            source_document_id=document.id,
            row_index=index,
            proposed_analyte_text=p.analyte_text,
            proposed_value_text=p.value_text,
            proposed_unit_text=p.unit_text,
            proposed_observed_at=p.observed_at,
            proposed_observed_at_is_date_only=p.observed_at_is_date_only,
            proposed_reference_low=p.reference_low,
            proposed_reference_high=p.reference_high,
            proposed_reference_text=p.reference_text,
            page=p.page,
            bbox=list(p.bbox) if p.bbox is not None else None,
            confidence=p.confidence,
            kpi_code=value.kpi_code,
            canonical_unit=value.canonical_unit,
            normalized_value=value.normalized_value,
            normalized_reference_low=value.normalized_reference_low,
            normalized_reference_high=value.normalized_reference_high,
            checks=[{"version": checks.CHECKS_VERSION}, *(c.as_dict() for c in value.checks)],
            status=value.status,
        )
        db.add(row)
        db.flush()
        value_ids.append(row.id)
        counts[value.status] += 1

    record_audit(
        db,
        action="intake.batch_proposed",
        actor_user_id=created_by_user_id,
        tenant_id=tenant_id,
        target_type="intake_batch",
        target_id=batch.id,
        correlation_id=correlation_id,
        detail={
            "source_document_id": str(document.id),
            "value_count": len(value_ids),
            "green": counts[PendingValueStatus.GREEN],
            "yellow": counts[PendingValueStatus.YELLOW],
            "red": counts[PendingValueStatus.RED],
            "extraction_provider": proposal.extraction_provider,
            "model_id": proposal.model_id,
            "prompt_version": proposal.prompt_version,
            "shadow": shadow,
        },
    )
    return BatchResult(
        batch_id=batch.id,
        value_ids=value_ids,
        green=counts[PendingValueStatus.GREEN],
        yellow=counts[PendingValueStatus.YELLOW],
        red=counts[PendingValueStatus.RED],
    )


def _observed_at(value: datetime | None, date_only: bool) -> datetime | None:
    """A day-only value is stored as that calendar day at UTC midnight (imports_routes
    `_observed_at`); a timed value keeps its zone, UTC when it named none."""
    if value is None:
        return None
    if date_only:
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def pending_values_of(db: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> list[PendingValue]:
    """The values of one batch in row order (tenant-scoped)."""
    return list(
        db.execute(
            select(PendingValue)
            .where(PendingValue.tenant_id == tenant_id, PendingValue.batch_id == batch_id)
            .order_by(PendingValue.row_index)
        ).scalars()
    )
