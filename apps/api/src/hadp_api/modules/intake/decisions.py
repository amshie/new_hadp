"""The human side of the gate: a clinician decides a pending value, and only then does it
become an observation.

Three decisions, one per value, append-only (`intake_decisions`):

- **confirmed** — the proposal as it stands. Refused for a red value. The checks run again at
  this moment against the record as it now is (a duplicate may have appeared since the
  proposal); a value that is red now is refused too.
- **corrected** — the clinician's own reading of the document. The checks run on the corrected
  reading with the clinician's confidence; the page checks are recorded but do not block (a
  human reads a scan the text layer cannot), every other red reason does. The proposal and the
  final reading are kept side by side so the proposal's error can be measured later.
- **rejected** — nothing enters the record; the reason is from a closed set.

A confirmed or corrected value becomes an `Observation` with `review_status = published`,
the source representation as the clinician saw it, the normalized value the checks computed,
the page and box as its locator, and the pending value and decision as its lineage. Nothing
here is reachable by the agent: these functions are called by the API under a clinician's
session only.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from PIL import ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, NotFound, ValidationFailed
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.documents.pdf_render import open_pdf
from hadp_api.modules.documents.pdf_text import PdfUnreadable, page_words
from hadp_api.modules.enums import (
    IntakeDecisionKind,
    IntakeRejectionReason,
    PendingValueStatus,
    ReviewStatus,
    ValueType,
)
from hadp_api.modules.imports import matching
from hadp_api.modules.imports.service import source_reference_text
from hadp_api.modules.intake import checks
from hadp_api.modules.intake.locate import line_extent
from hadp_api.modules.intake.models import IntakeBatch, IntakeDecision, PendingValue
from hadp_api.modules.intake.pages import OcrUnavailable, load_pages
from hadp_api.modules.intake.service import _DbBounds, record_view
from hadp_api.modules.kpi.service import load_terminology
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient

# Red reasons a CORRECTION may carry and still be recorded: they say the text layer does not
# show what the clinician read — true of every scan — and the clinician is the reader now.
_PAGE_REASONS = frozenset(
    {"no_page_text", "analyte_not_on_page", "value_not_on_page", "unit_not_on_page"}
)
# The confidence of a human reading.
_HUMAN_CONFIDENCE = Decimal("1")


@dataclass(frozen=True)
class CorrectionIn:
    """What the clinician changed. A field left None keeps the proposal's."""

    analyte_text: str | None = None
    value_text: str | None = None
    unit_text: str | None = None
    observed_at: datetime | None = None
    observed_at_is_date_only: bool | None = None
    reference_low: str | None = None
    reference_high: str | None = None
    reference_text: str | None = None
    # True when the clinician cleared a field the proposal had (an empty unit, no reference).
    clear_unit: bool = False
    clear_reference: bool = False


def _load_value(db: Session, tenant_id: uuid.UUID, pending_value_id: uuid.UUID) -> PendingValue:
    value = db.execute(
        select(PendingValue).where(
            PendingValue.id == pending_value_id, PendingValue.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if value is None:
        raise NotFound("pending value not found")
    return value


def _already_decided(db: Session, pending_value_id: uuid.UUID) -> bool:
    return (
        db.execute(
            select(IntakeDecision.id).where(IntakeDecision.pending_value_id == pending_value_id)
        ).first()
        is not None
    )


def _proposal_of(value: PendingValue) -> checks.ProposedValue:
    return checks.ProposedValue(
        analyte_text=value.proposed_analyte_text,
        value_text=value.proposed_value_text,
        unit_text=value.proposed_unit_text,
        observed_at=value.proposed_observed_at,
        observed_at_is_date_only=value.proposed_observed_at_is_date_only,
        page=value.page,
        confidence=Decimal(value.confidence),
        reference_low=value.proposed_reference_low,
        reference_high=value.proposed_reference_high,
        reference_text=value.proposed_reference_text,
        bbox=tuple(value.bbox) if value.bbox else None,  # type: ignore[arg-type]
    )


def _apply(proposal: checks.ProposedValue, correction: CorrectionIn) -> checks.ProposedValue:
    observed_at = (
        correction.observed_at if correction.observed_at is not None else proposal.observed_at
    )
    date_only = (
        correction.observed_at_is_date_only
        if correction.observed_at_is_date_only is not None
        else proposal.observed_at_is_date_only
    )
    if observed_at is not None:
        observed_at = (
            datetime(observed_at.year, observed_at.month, observed_at.day, tzinfo=UTC)
            if date_only
            else (observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=UTC))
        )
    return checks.ProposedValue(
        analyte_text=correction.analyte_text or proposal.analyte_text,
        value_text=correction.value_text or proposal.value_text,
        unit_text=None if correction.clear_unit else (correction.unit_text or proposal.unit_text),
        observed_at=observed_at,
        observed_at_is_date_only=date_only,
        page=proposal.page,
        confidence=_HUMAN_CONFIDENCE,
        reference_low=None
        if correction.clear_reference
        else (correction.reference_low or proposal.reference_low),
        reference_high=None
        if correction.clear_reference
        else (correction.reference_high or proposal.reference_high),
        reference_text=None
        if correction.clear_reference
        else (correction.reference_text or proposal.reference_text),
        bbox=proposal.bbox,
    )


def _as_dict(value: checks.ProposedValue) -> dict[str, Any]:
    return {
        "analyte_text": value.analyte_text,
        "value_text": value.value_text,
        "unit_text": value.unit_text,
        "observed_at": value.observed_at.isoformat() if value.observed_at else None,
        "observed_at_is_date_only": value.observed_at_is_date_only,
        "reference_low": value.reference_low,
        "reference_high": value.reference_high,
        "reference_text": value.reference_text,
    }


def _recheck(
    db: Session, batch: IntakeBatch, patient: Patient, value: checks.ProposedValue, today: date
) -> checks.CheckedValue:
    document = db.get(SourceDocument, batch.source_document_id)
    if document is None:
        raise NotFound("source document not found")
    store = get_blob_store(get_settings())
    if not store.exists(document.storage_key):
        raise Conflict("document_unavailable: the stored source document cannot be read")
    try:
        pages = load_pages(store.get(document.storage_key), get_settings())
    except PdfUnreadable as exc:
        raise ValidationFailed(f"document_unreadable: {exc.detail}") from exc
    except OcrUnavailable as exc:
        raise Conflict(f"ocr_unavailable: {exc.detail}") from exc
    checked = checks.run_checks(
        checks.ProposedBatch(
            values=(value,),
            patient_date_of_birth=batch.proposed_patient_date_of_birth,
            issue_date=batch.proposed_issue_date,
        ),
        terminology=load_terminology(db),
        bounds=_DbBounds(db),
        record=record_view(db, patient),
        pages=pages,
        today=today,
    )
    return checked.values[0]


def _locator(value: PendingValue) -> str:
    text = f"page {value.page}"
    if value.bbox:
        text += " bbox " + ",".join(f"{float(x):.1f}" for x in value.bbox)
    return text[:255]


def _observation(
    *,
    pending: PendingValue,
    final: checks.ProposedValue,
    checked: checks.CheckedValue,
    now: datetime,
) -> Observation:
    if final.observed_at is None:
        raise Conflict("date_missing: a value without a sampling date cannot enter the record")
    return Observation(
        tenant_id=pending.tenant_id,
        patient_id=pending.patient_id,
        source_document_id=pending.source_document_id,
        source_record_locator=_locator(pending),
        original_name=final.analyte_text,
        original_value=final.value_text,
        original_unit=final.unit_text,
        reference_text=source_reference_text(
            final.reference_text, final.reference_low, final.reference_high, final.unit_text
        ),
        metric_code=None,
        code_system=None,
        kpi_code=checked.kpi_code,
        mapping_confidence=1.0 if checked.kpi_code is not None else None,
        value_type=ValueType.NUMERIC,
        numeric_value=checked.numeric_value,
        normalized_value=checked.normalized_value,
        normalized_unit=checked.canonical_unit if checked.normalized_value is not None else None,
        reference_low=checked.normalized_reference_low,
        reference_high=checked.normalized_reference_high,
        normalization_version=checks.CHECKS_VERSION,
        observed_at=final.observed_at,
        observed_at_is_date_only=final.observed_at_is_date_only,
        received_at=now,
        review_status=ReviewStatus.PUBLISHED,
    )


def decide(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    pending_value_id: uuid.UUID,
    decision: IntakeDecisionKind,
    decided_by_user_id: uuid.UUID,
    correction: CorrectionIn | None = None,
    rejection_reason: IntakeRejectionReason | None = None,
    review_seconds: int | None = None,
    screen_seconds: int | None = None,
    correlation_id: str | None = None,
    today: date | None = None,
    auto_accept_rule_id: uuid.UUID | None = None,
) -> IntakeDecision:
    """One attributable decision on one pending value. Raises Conflict when the value is
    already decided, when a red value is confirmed as it stands, or when the checks refuse the
    reading now; NotFound outside the tenant."""
    if auto_accept_rule_id is not None and decision is not IntakeDecisionKind.CONFIRMED:
        raise Conflict("rule_only_confirms: a rule never corrects or rejects")
    pending = _load_value(db, tenant_id, pending_value_id)
    matching.lock_patient_record(db, pending.patient_id)
    if _already_decided(db, pending.id):
        raise Conflict("already_decided: this value has a decision")
    batch = db.get(IntakeBatch, pending.batch_id)
    patient = db.get(Patient, pending.patient_id)
    if batch is None or patient is None:
        raise NotFound("pending value not found")
    if batch.shadow:
        raise Conflict("shadow_batch: a shadow batch is compared, never decided")
    now = datetime.now(UTC)
    day = today or now.date()

    observation: Observation | None = None
    correction_record: dict[str, Any] | None = None
    if decision is IntakeDecisionKind.REJECTED:
        if rejection_reason is None:
            raise ValidationFailed("rejection_reason is required")
    elif decision is IntakeDecisionKind.CONFIRMED:
        if pending.status is PendingValueStatus.RED:
            raise Conflict("red_value: a red value is corrected or rejected, never confirmed")
        final = _proposal_of(pending)
        checked = _recheck(db, batch, patient, final, day)
        reds = sorted({c.reason for c in checked.checks if c.severity == checks.RED and c.reason})
        if reds:
            raise Conflict("checks_failed: " + ", ".join(reds))
        observation = _observation(pending=pending, final=final, checked=checked, now=now)
    else:
        if correction is None:
            raise ValidationFailed("correction is required")
        proposal = _proposal_of(pending)
        final = _apply(proposal, correction)
        if _as_dict(final) == _as_dict(proposal):
            raise Conflict("no_change: the correction leaves the proposal as it is")
        checked = _recheck(db, batch, patient, final, day)
        reds = sorted({c.reason for c in checked.checks if c.severity == checks.RED and c.reason})
        blocking = [r for r in reds if r not in _PAGE_REASONS]
        if blocking:
            raise Conflict("checks_failed: " + ", ".join(blocking))
        observation = _observation(pending=pending, final=final, checked=checked, now=now)
        correction_record = {
            "original": _as_dict(proposal),
            "final": _as_dict(final),
            "page_check": [r for r in reds if r in _PAGE_REASONS],
            "checks_version": checks.CHECKS_VERSION,
        }

    if observation is not None:
        db.add(observation)
        db.flush()
    row = IntakeDecision(
        tenant_id=tenant_id,
        patient_id=pending.patient_id,
        batch_id=pending.batch_id,
        pending_value_id=pending.id,
        decision=decision,
        observation_id=observation.id if observation is not None else None,
        correction=correction_record,
        rejection_reason=rejection_reason if decision is IntakeDecisionKind.REJECTED else None,
        decided_by_user_id=decided_by_user_id,
        review_seconds=review_seconds,
        screen_seconds=screen_seconds,
        auto_accept_rule_id=auto_accept_rule_id,
    )
    db.add(row)
    db.flush()
    detail = {
        "batch_id": str(pending.batch_id),
        "observation_id": str(observation.id) if observation is not None else None,
        "status_at_proposal": pending.status.value,
        "rejection_reason": rejection_reason.value if rejection_reason else None,
        "review_seconds": review_seconds,
        "screen_seconds": screen_seconds,
    }
    # One literal action per decision: the trail's vocabulary is read from the source
    # (tests/test_audit_read.py), so the action is never assembled from a value.
    if auto_accept_rule_id is not None:
        record_audit(
            db,
            action="intake.value_auto_accepted",
            actor_user_id=decided_by_user_id,
            tenant_id=tenant_id,
            target_type="pending_value",
            target_id=pending.id,
            correlation_id=correlation_id,
            detail={**detail, "auto_accept_rule_id": str(auto_accept_rule_id)},
        )
    elif decision is IntakeDecisionKind.CONFIRMED:
        record_audit(
            db,
            action="intake.value_confirmed",
            actor_user_id=decided_by_user_id,
            tenant_id=tenant_id,
            target_type="pending_value",
            target_id=pending.id,
            correlation_id=correlation_id,
            detail=detail,
        )
    elif decision is IntakeDecisionKind.CORRECTED:
        record_audit(
            db,
            action="intake.value_corrected",
            actor_user_id=decided_by_user_id,
            tenant_id=tenant_id,
            target_type="pending_value",
            target_id=pending.id,
            correlation_id=correlation_id,
            detail=detail,
        )
    else:
        record_audit(
            db,
            action="intake.value_rejected",
            actor_user_id=decided_by_user_id,
            tenant_id=tenant_id,
            target_type="pending_value",
            target_id=pending.id,
            correlation_id=correlation_id,
            detail=detail,
        )
    return row


def confirm_green(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    batch_id: uuid.UUID,
    decided_by_user_id: uuid.UUID,
    screen_seconds: int | None = None,
    correlation_id: str | None = None,
    today: date | None = None,
) -> list[IntakeDecision]:
    """Confirm every undecided GREEN value of a batch, one decision each (one click for the
    clinician, one audit event per value). A value the checks refuse now is skipped and left
    undecided — it shows up on the screen with its new reason."""
    batch = db.execute(
        select(IntakeBatch).where(IntakeBatch.id == batch_id, IntakeBatch.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if batch is None:
        raise NotFound("batch not found")
    if batch.shadow:
        raise Conflict("shadow_batch: a shadow batch is compared, never decided")
    decided: list[IntakeDecision] = []
    for value in db.execute(
        select(PendingValue)
        .where(PendingValue.batch_id == batch.id, PendingValue.status == PendingValueStatus.GREEN)
        .order_by(PendingValue.row_index)
    ).scalars():
        if _already_decided(db, value.id):
            continue
        try:
            with db.begin_nested():
                decided.append(
                    decide(
                        db,
                        tenant_id=tenant_id,
                        pending_value_id=value.id,
                        decision=IntakeDecisionKind.CONFIRMED,
                        decided_by_user_id=decided_by_user_id,
                        screen_seconds=screen_seconds,
                        correlation_id=correlation_id,
                        today=today,
                    )
                )
        except Conflict:
            continue
    return decided


# --- Reading, for the confirmation screen ---------------------------------------------------------


def list_batches(
    db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(IntakeBatch, SourceDocument.filename)
        .join(SourceDocument, SourceDocument.id == IntakeBatch.source_document_id)
        .where(
            IntakeBatch.tenant_id == tenant_id,
            IntakeBatch.patient_id == patient_id,
            IntakeBatch.shadow.is_(False),
        )
        .order_by(IntakeBatch.created_at.desc(), IntakeBatch.id)
    ).all()
    out: list[dict[str, Any]] = []
    for batch, filename in rows:
        values = db.execute(
            select(PendingValue.id, PendingValue.status).where(PendingValue.batch_id == batch.id)
        ).all()
        decided = set(
            db.execute(
                select(IntakeDecision.pending_value_id).where(IntakeDecision.batch_id == batch.id)
            ).scalars()
        )
        counts = dict.fromkeys(PendingValueStatus, 0)
        for _id, status in values:
            counts[status] += 1
        out.append(
            {
                "batch_id": batch.id,
                "document_id": batch.source_document_id,
                "filename": filename,
                "created_at": batch.created_at,
                "extraction_provider": batch.extraction_provider,
                "model_id": batch.model_id,
                "value_count": len(values),
                "green": counts[PendingValueStatus.GREEN],
                "yellow": counts[PendingValueStatus.YELLOW],
                "red": counts[PendingValueStatus.RED],
                "open_count": sum(1 for v_id, _s in values if v_id not in decided),
            }
        )
    return out


def batch_view(db: Session, *, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> dict[str, Any]:
    row = db.execute(
        select(IntakeBatch, SourceDocument.filename, Patient.display_name)
        .join(SourceDocument, SourceDocument.id == IntakeBatch.source_document_id)
        .join(Patient, Patient.id == IntakeBatch.patient_id)
        .where(
            IntakeBatch.id == batch_id,
            IntakeBatch.tenant_id == tenant_id,
            IntakeBatch.shadow.is_(False),
        )
    ).first()
    if row is None:
        raise NotFound("batch not found")
    batch, filename, patient_name = row
    decisions = {
        d.pending_value_id: d
        for d in db.execute(
            select(IntakeDecision).where(IntakeDecision.batch_id == batch.id)
        ).scalars()
    }
    values = []
    for v in db.execute(
        select(PendingValue)
        .where(PendingValue.batch_id == batch.id)
        .order_by(PendingValue.row_index)
    ).scalars():
        d = decisions.get(v.id)
        values.append(
            {
                "pending_value_id": v.id,
                "row_index": v.row_index,
                "analyte_text": v.proposed_analyte_text,
                "value_text": v.proposed_value_text,
                "unit_text": v.proposed_unit_text,
                "observed_at": v.proposed_observed_at,
                "observed_at_is_date_only": v.proposed_observed_at_is_date_only,
                "reference_low": v.proposed_reference_low,
                "reference_high": v.proposed_reference_high,
                "reference_text": v.proposed_reference_text,
                "page": v.page,
                "has_region": bool(v.bbox),
                "confidence": v.confidence,
                "kpi_code": v.kpi_code,
                "canonical_unit": v.canonical_unit,
                "normalized_value": v.normalized_value,
                "status": v.status,
                "reasons": [c["reason"] for c in v.checks if c.get("reason")],
                "decision": d.decision if d else None,
                "decided_at": d.created_at if d else None,
                "observation_id": d.observation_id if d else None,
                "rejection_reason": d.rejection_reason if d else None,
                "corrected_to": (d.correction or {}).get("final") if d else None,
            }
        )
    return {
        "batch_id": batch.id,
        "patient_id": batch.patient_id,
        "patient_display_name": patient_name,
        "document_id": batch.source_document_id,
        "filename": filename,
        "created_at": batch.created_at,
        "extraction_provider": batch.extraction_provider,
        "model_id": batch.model_id,
        "prompt_version": batch.prompt_version,
        "source_lab": batch.source_lab,
        "page_count": batch.page_count,
        "proposed_patient_date_of_birth": batch.proposed_patient_date_of_birth,
        "proposed_issue_date": batch.proposed_issue_date,
        "batch_reasons": [c["reason"] for c in batch.checks if c.get("reason")],
        "values": values,
        "open_count": sum(1 for v in values if v["decision"] is None),
    }


# The region around a value: its whole printed row (the analyte's name included), a little
# above and below. Points.
_PAD_X = 12.0
_PAD_Y = 14.0
_REGION_DPI = 144
# The located value is framed in the crop: a neutral colour, never a status colour.
_FRAME_RGB = (29, 78, 216)
_FRAME_PX = 2
_FRAME_MARGIN = 2.0  # points around the value's box


def region_png(db: Session, *, tenant_id: uuid.UUID, pending_value_id: uuid.UUID) -> bytes:
    """A crop of the cited page around the value's box — the clinician's view of where the
    number came from (`render_region`)."""
    value = _load_value(db, tenant_id, pending_value_id)
    document = db.get(SourceDocument, value.source_document_id)
    if document is None:
        raise NotFound("source document not found")
    store = get_blob_store(get_settings())
    if not store.exists(document.storage_key):
        raise Conflict("document_unavailable: the stored source document cannot be read")
    box: tuple[float, float, float, float] | None = None
    if value.bbox:
        x0, y0, x1, y1 = (float(x) for x in value.bbox)
        box = (x0, y0, x1, y1)
    return render_region(store.get(document.storage_key), value.page, box)


def render_region(
    data: bytes, page_no: int, bbox: tuple[float, float, float, float] | None
) -> bytes:
    """PNG of the whole printed row the box sits on, a little above and below, with the value
    framed. Without a box (a scan, or a value code could not place with certainty): the whole
    page, unframed. NotFound for a page the document does not have."""
    with open_pdf(data) as pdf:
        if page_no < 1 or page_no > len(pdf.pages):
            raise NotFound("page not found")
        page = pdf.pages[page_no - 1]
        frame: tuple[float, float, float, float] | None = None
        if bbox is not None:
            x0, y0, x1, y1 = bbox
            left, right = line_extent(page_words(page), bbox)
            box = (
                max(0.0, left - _PAD_X),
                max(0.0, y0 - _PAD_Y),
                min(float(page.width), right + _PAD_X),
                min(float(page.height), y1 + _PAD_Y),
            )
            page = page.crop(box)
            frame = (x0 - box[0], y0 - box[1], x1 - box[0], y1 - box[1])
        image = page.to_image(resolution=_REGION_DPI).original.convert("RGB")
        if frame is not None:
            scale = _REGION_DPI / 72
            ImageDraw.Draw(image).rectangle(
                [
                    round((frame[0] - _FRAME_MARGIN) * scale),
                    round((frame[1] - _FRAME_MARGIN) * scale),
                    round((frame[2] + _FRAME_MARGIN) * scale),
                    round((frame[3] + _FRAME_MARGIN) * scale),
                ],
                outline=_FRAME_RGB,
                width=_FRAME_PX,
            )
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
