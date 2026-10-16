"""Shadow mode: proposals nobody sees, compared later with what a person keyed independently.

A shadow batch is a proposal written with `shadow=True`: it is checked and stored like any
other, but the confirmation screen never lists it and no decision can be made on it. A
clinician enters the same report's values the way the clinic does today (structured import or
manual entry), and afterwards `compare` sets the two side by side:

- per laboratory and per field, how often the proposal and the keyed value agree
  (**divergence** = 1 − agreement), over the values that could be matched by analyte and
  sampling day; proposals without a keyed counterpart and keyed values without a proposal are
  counted too;
- the time the clinic's own path took: from the document's upload to the first keyed value of
  that patient published afterwards (**keying delay**) — the figure a confirmation-screen
  `review_seconds` is later compared with.

Counts, rates and timings only. The comparison never writes anything.
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import ReviewStatus
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.intake import checks
from hadp_api.modules.intake.error_rates import UNKNOWN_LAB
from hadp_api.modules.intake.models import IntakeBatch, IntakeDecision, PendingValue
from hadp_api.modules.observations.models import Observation

FIELDS = ("value_text", "unit_text", "reference_low", "reference_high")


@dataclass
class LabDivergence:
    source_lab: str
    batches: int = 0
    proposed: int = 0
    keyed: int = 0
    matched: int = 0
    field_agree: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    keying_delays_seconds: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_lab": self.source_lab,
            "batches": self.batches,
            "proposed": self.proposed,
            "keyed": self.keyed,
            "matched": self.matched,
            "unmatched_proposed": self.proposed - self.matched,
            "unmatched_keyed": self.keyed - self.matched,
            "field_divergence": {
                f: (1 - self.field_agree[f] / self.matched) if self.matched else None
                for f in FIELDS
            },
            "keying_delay_seconds_median": (
                statistics.median(self.keying_delays_seconds)
                if self.keying_delays_seconds
                else None
            ),
            "keying_delay_samples": len(self.keying_delays_seconds),
        }


def _day(value: datetime | None) -> str | None:
    # Date-only values are stored at midnight UTC; a timed value is compared by its UTC day,
    # the same way the duplicate check compares (checks.py).
    return value.astimezone(UTC).date().isoformat() if value is not None else None


def _number(text: str | None) -> Decimal | None:
    if text is None:
        return None
    try:
        return Decimal(" ".join(str(text).split()).replace(",", "."))
    except InvalidOperation:
        return None


def _same_number(proposed: str | None, keyed: Decimal | str | None) -> bool:
    a = _number(proposed)
    b = keyed if isinstance(keyed, Decimal) or keyed is None else _number(keyed)
    if a is None or b is None:
        return a is None and b is None and _plain(proposed) == _plain(keyed)
    return a == b


def _plain(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def _unit(value: str | None) -> str:
    return normalize_mod.canonical_unit_spelling(value) or _plain(value)


def compare(db: Session, *, tenant_id: uuid.UUID) -> list[LabDivergence]:
    """Every shadow batch of this clinic against the published observations of its patient that
    a person keyed independently — every published observation except those an intake
    decision confirmed (the only way a proposal itself enters the record)."""
    confirmed = select(IntakeDecision.observation_id).where(
        IntakeDecision.observation_id.is_not(None)
    )
    batches = db.execute(
        select(IntakeBatch, SourceDocument)
        .join(SourceDocument, SourceDocument.id == IntakeBatch.source_document_id)
        .where(IntakeBatch.tenant_id == tenant_id, IntakeBatch.shadow.is_(True))
        .order_by(IntakeBatch.created_at, IntakeBatch.id)
    ).all()
    labs: dict[str, LabDivergence] = {}
    for batch, document in batches:
        lab = batch.source_lab or UNKNOWN_LAB
        agg = labs.setdefault(lab, LabDivergence(source_lab=lab))
        agg.batches += 1
        proposals = list(
            db.execute(
                select(PendingValue)
                .where(PendingValue.batch_id == batch.id)
                .order_by(PendingValue.row_index)
            ).scalars()
        )
        keyed = list(
            db.execute(
                select(Observation)
                .where(
                    Observation.patient_id == batch.patient_id,
                    Observation.review_status == ReviewStatus.PUBLISHED,
                    Observation.id.not_in(confirmed),
                )
                .order_by(Observation.received_at, Observation.id)
            ).scalars()
        )
        agg.proposed += len(proposals)
        agg.keyed += len(keyed)
        after_upload = [o.received_at for o in keyed if o.received_at > document.created_at]
        if after_upload:
            agg.keying_delays_seconds.append(
                (min(after_upload) - document.created_at).total_seconds()
            )
        remaining = list(keyed)
        for p in proposals:
            p_day = _day(p.proposed_observed_at)
            hit = next(
                (
                    o
                    for o in remaining
                    if (
                        (p.kpi_code is not None and o.kpi_code == p.kpi_code)
                        or checks.analyte_key(o.original_name)
                        == checks.analyte_key(p.proposed_analyte_text)
                    )
                    and _day(o.observed_at) == p_day
                ),
                None,
            )
            if hit is None:
                continue
            remaining.remove(hit)
            agg.matched += 1
            if _same_number(p.proposed_value_text, hit.original_value):
                agg.field_agree["value_text"] += 1
            if _unit(p.proposed_unit_text) == _unit(hit.original_unit):
                agg.field_agree["unit_text"] += 1
            if _same_number(p.proposed_reference_low, hit.reference_low):
                agg.field_agree["reference_low"] += 1
            if _same_number(p.proposed_reference_high, hit.reference_high):
                agg.field_agree["reference_high"] += 1
    return [labs[k] for k in sorted(labs)]
