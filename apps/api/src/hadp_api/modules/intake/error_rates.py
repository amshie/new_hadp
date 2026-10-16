"""The error-rate report: how often a proposal was wrong, per laboratory, per KPI, per field.

Every decision a clinician made is a label: confirmed means the proposal was right as it stood;
corrected names the fields that were wrong (the proposal and the final reading are stored side
by side); rejected means the value should not have been proposed at all. From those labels this
module computes, per stratum (laboratory as the document named it, KPI as the catalog mapped it):

- per **field**: how many decided values changed that field (value, unit, date, reference
  bounds, name) — the field error rate;
- for **green** values: how many were confirmed unchanged, how many were corrected or rejected —
  the green error rate, with the upper bound of a 95 % Wilson interval. This is the number an
  auto-acceptance rule is measured against (`auto_accept.py`): a stratum qualifies only when the
  upper bound is under the rule's threshold over at least the rule's sample.

Counts and rates only; no value leaves this module. Decisions made by a rule are counted
separately (`auto_confirmed`) and never feed the green error rate — a rule cannot grade itself.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import IntakeDecisionKind, PendingValueStatus
from hadp_api.modules.intake.models import IntakeBatch, IntakeDecision, PendingValue

FIELDS = (
    "analyte_text",
    "value_text",
    "unit_text",
    "observed_at",
    "reference_low",
    "reference_high",
)
UNKNOWN_LAB = "(unknown)"
UNMAPPED = "(unmapped)"


def wilson_upper(errors: int, n: int, z: float = 1.959964) -> float:
    """Upper bound of the Wilson score interval for a proportion — 1.0 for an empty sample."""
    if n <= 0:
        return 1.0
    p = errors / n
    denominator = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (centre + spread) / denominator)


@dataclass
class StratumRates:
    source_lab: str
    kpi_code: str
    decided: int = 0
    confirmed: int = 0
    corrected: int = 0
    rejected: int = 0
    auto_confirmed: int = 0
    field_errors: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    green_decided: int = 0
    green_errors: int = 0
    first_decision_at: datetime | None = None
    last_decision_at: datetime | None = None

    @property
    def green_error_rate(self) -> float | None:
        return self.green_errors / self.green_decided if self.green_decided else None

    @property
    def green_error_upper_95(self) -> float:
        return wilson_upper(self.green_errors, self.green_decided)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_lab": self.source_lab,
            "kpi_code": self.kpi_code,
            "decided": self.decided,
            "confirmed": self.confirmed,
            "corrected": self.corrected,
            "rejected": self.rejected,
            "auto_confirmed": self.auto_confirmed,
            "field_error_rates": {
                f: (self.field_errors[f] / self.decided if self.decided else None) for f in FIELDS
            },
            "field_errors": dict(self.field_errors),
            "green_decided": self.green_decided,
            "green_errors": self.green_errors,
            "green_error_rate": self.green_error_rate,
            "green_error_upper_95": self.green_error_upper_95,
            "first_decision_at": self.first_decision_at,
            "last_decision_at": self.last_decision_at,
        }


def _changed_fields(correction: dict[str, Any] | None) -> set[str]:
    if not correction:
        return set()
    original = correction.get("original") or {}
    final = correction.get("final") or {}
    changed = set()
    for f in FIELDS:
        a, b = original.get(f), final.get(f)
        if f == "observed_at":
            a, b = (str(a)[:10] if a else None), (str(b)[:10] if b else None)
        if (a or None) != (b or None):
            changed.add(f)
    return changed


def error_rates(
    db: Session, *, tenant_id: uuid.UUID, source_lab: str | None = None
) -> list[StratumRates]:
    """Every stratum of this clinic with at least one decision, ordered by laboratory and KPI.
    Shadow batches carry no decisions and so do not appear."""
    rows = db.execute(
        select(IntakeDecision, PendingValue, IntakeBatch)
        .join(PendingValue, PendingValue.id == IntakeDecision.pending_value_id)
        .join(IntakeBatch, IntakeBatch.id == IntakeDecision.batch_id)
        .where(IntakeDecision.tenant_id == tenant_id)
        .order_by(IntakeDecision.created_at, IntakeDecision.id)
    ).all()
    strata: dict[tuple[str, str], StratumRates] = {}
    for decision, value, batch in rows:
        lab = batch.source_lab or UNKNOWN_LAB
        if source_lab is not None and lab != source_lab:
            continue
        kpi = value.kpi_code or UNMAPPED
        s = strata.setdefault((lab, kpi), StratumRates(source_lab=lab, kpi_code=kpi))
        s.decided += 1
        s.first_decision_at = s.first_decision_at or decision.created_at
        s.last_decision_at = decision.created_at
        if decision.auto_accept_rule_id is not None:
            s.auto_confirmed += 1
            continue
        if decision.decision is IntakeDecisionKind.CONFIRMED:
            s.confirmed += 1
        elif decision.decision is IntakeDecisionKind.CORRECTED:
            s.corrected += 1
            for f in _changed_fields(decision.correction):
                s.field_errors[f] += 1
        else:
            s.rejected += 1
            # A rejected proposal was wrong in what it claimed to be: its value and its name.
            s.field_errors["value_text"] += 1
            s.field_errors["analyte_text"] += 1
        if value.status is PendingValueStatus.GREEN:
            s.green_decided += 1
            if decision.decision is not IntakeDecisionKind.CONFIRMED:
                s.green_errors += 1
    return [strata[key] for key in sorted(strata)]
