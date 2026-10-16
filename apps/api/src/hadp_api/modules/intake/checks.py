"""Deterministic checks over values a model proposed from a document — code, no model.

Every proposed value passes the same fixed list of checks, each recording pass / fail /
skipped with a reason from a closed set. The checks never decide anything about the patient:
they decide whether the READING of the document can be trusted enough to show a human as
green, must be looked at (yellow), or has to be corrected or rejected (red). Nothing here
compares a value with its reference interval.

The status is computed from the checks and from the model's confidence; it is never taken
from the proposal. This module is pure: the catalog, the bounds, the patient's record and the
page texts come in through small protocols, so the golden cases run without a database.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from hadp_api.modules.enums import PendingValueStatus
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.kpi.terms import CatalogTerm

# --- Closed vocabularies ---------------------------------------------------------------------

# The checks, in the order they run.
PAGE_CITED = "page_cited"
ON_PAGE = "on_page"
MAPPING = "mapping"
VALUE = "value"
UNIT = "unit"
REFERENCE = "reference"
PLAUSIBILITY = "plausibility"
DELTA = "delta"
DATE = "date"
DUPLICATE = "duplicate"
CONFIDENCE = "confidence"
# Batch-level, recorded on the batch and on every value of it.
PATIENT_MATCH = "patient_match"

CHECKS: tuple[str, ...] = (
    PATIENT_MATCH,
    PAGE_CITED,
    ON_PAGE,
    MAPPING,
    VALUE,
    UNIT,
    REFERENCE,
    PLAUSIBILITY,
    DELTA,
    DATE,
    DUPLICATE,
    CONFIDENCE,
)

PASS = "pass"
FAIL = "fail"
SKIPPED = "skipped"

RED = PendingValueStatus.RED.value
YELLOW = PendingValueStatus.YELLOW.value

# Reasons (closed). The severity each one carries is fixed here, not chosen per call.
REASONS: dict[str, str] = {
    "patient_mismatch": RED,
    "patient_dob_not_proposed": YELLOW,
    "page_out_of_range": RED,
    "no_page_text": RED,
    "analyte_not_on_page": RED,
    "value_not_on_page": RED,
    "unit_not_on_page": RED,
    "page_text_from_ocr": YELLOW,
    "unmapped_analyte": YELLOW,
    "value_not_a_number": RED,
    "unit_missing": RED,
    "unit_unknown": RED,
    "reference_unreadable": YELLOW,
    "outside_hard_bounds": RED,
    "plausibility_not_configured": YELLOW,
    "implausible_delta": YELLOW,
    "date_missing": RED,
    "date_in_future": YELLOW,
    "date_after_issue": YELLOW,
    "date_outside_window": YELLOW,
    "date_before_birth": RED,
    "duplicate_of_published": RED,
    "duplicate_in_batch": RED,
    "conflicting_in_batch": YELLOW,
    "low_confidence": YELLOW,
}

# A value is green only at or above this confidence (the model's own, 0..1).
GREEN_CONFIDENCE = Decimal("0.9")
# A sampling date this long before the document's issue date asks a human to look.
ISSUE_WINDOW = timedelta(days=90)
# The ruleset's version, written into every check list so a result stays reproducible.
CHECKS_VERSION = "intake-checks-1"


# --- Inputs ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProposedValue:
    """One value as the model read it. Text as written; nothing normalized."""

    analyte_text: str
    value_text: str
    unit_text: str | None
    observed_at: datetime | None
    observed_at_is_date_only: bool
    page: int
    confidence: Decimal
    reference_low: str | None = None
    reference_high: str | None = None
    reference_text: str | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class ProposedBatch:
    values: tuple[ProposedValue, ...]
    patient_date_of_birth: date | None = None
    issue_date: date | None = None


@dataclass(frozen=True)
class PlausibilityBound:
    unit: str
    hard_low: Decimal | None
    hard_high: Decimal | None
    delta_max_relative: Decimal | None


@dataclass(frozen=True)
class PriorValue:
    """The last value the record holds for a KPI, in the unit it is held in."""

    value: Decimal
    unit: str
    observed_at: datetime | None
    observation_id: uuid.UUID | None = None


class Terminology(Protocol):
    def resolve(self, source_name: str) -> CatalogTerm | None: ...


class Bounds(Protocol):
    def for_kpi(self, kpi_code: str) -> PlausibilityBound | None: ...


class PatientRecordView(Protocol):
    """What the checks may know about the patient: the date of birth, the last published
    value per KPI, and whether a value is already published. Never another patient."""

    @property
    def date_of_birth(self) -> date | None: ...

    def last_published(self, kpi_code: str) -> PriorValue | None: ...

    def is_published(
        self,
        *,
        kpi_code: str | None,
        analyte_key: str,
        day: date | None,
        value_text: str,
        unit_text: str | None,
    ) -> bool: ...


class PageTexts(Protocol):
    @property
    def page_count(self) -> int: ...

    def text(self, page: int) -> str:
        """The text of a 1-based page as the document reader produced it ('' when the page
        has no text layer and no OCR ran)."""
        ...

    def source(self, page: int) -> str:
        """Where the page's text came from: "text_layer", "ocr" or "none"."""
        ...


# --- Outputs ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    check: str
    result: str
    reason: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> str | None:
        return REASONS[self.reason] if self.reason is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "result": self.result,
            "severity": self.severity,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CheckedValue:
    proposal: ProposedValue
    kpi_code: str | None
    canonical_unit: str | None
    # The written value as one number in the WRITTEN unit (None when it is not one number).
    numeric_value: Decimal | None
    normalized_value: Decimal | None
    normalized_reference_low: Decimal | None
    normalized_reference_high: Decimal | None
    checks: tuple[CheckResult, ...]
    status: PendingValueStatus


@dataclass(frozen=True)
class CheckedBatch:
    checks: tuple[CheckResult, ...]
    values: tuple[CheckedValue, ...]


# --- Helpers ---------------------------------------------------------------------------------


def _ok(check: str, **detail: Any) -> CheckResult:
    return CheckResult(check, PASS, None, detail)


def _fail(check: str, reason: str, **detail: Any) -> CheckResult:
    assert reason in REASONS, reason
    return CheckResult(check, FAIL, reason, detail)


def _skip(check: str, why: str) -> CheckResult:
    return CheckResult(check, SKIPPED, None, {"why": why})


def plain(value: Decimal) -> str:
    """A number as text without exponent, for check details and golden files."""
    return format(value.normalize(), "f") if value == value.to_integral() else format(value, "f")


def analyte_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def _squash(text: str) -> str:
    return " ".join(text.split())


_NUMBER_EDGE = r"(?<![0-9.,])"
_NUMBER_END = r"(?![0-9.,])"


def value_on_page(value_text: str, page_text: str) -> bool:
    """Whether the value, as written, stands on the page as a number of its own: '5,2' is not
    found inside '15,2' or '5,25'. Whitespace inside the value is not significant."""
    needle = _squash(value_text)
    if not needle:
        return False
    pattern = _NUMBER_EDGE + re.escape(needle) + _NUMBER_END
    return re.search(pattern, _squash(page_text)) is not None


def text_on_page(text: str, page_text: str) -> bool:
    """Whether a name or a unit stands on the page, letter case aside."""
    needle = _squash(text).casefold()
    return bool(needle) and needle in _squash(page_text).casefold()


def _day(value: ProposedValue) -> date | None:
    if value.observed_at is None:
        return None
    if value.observed_at_is_date_only:
        return value.observed_at.astimezone(UTC).date()
    return value.observed_at.date()


def status_of(checks: tuple[CheckResult, ...]) -> PendingValueStatus:
    severities = {c.severity for c in checks if c.severity is not None}
    if RED in severities:
        return PendingValueStatus.RED
    if YELLOW in severities:
        return PendingValueStatus.YELLOW
    return PendingValueStatus.GREEN


# --- The checks ------------------------------------------------------------------------------


def check_patient(batch: ProposedBatch, record: PatientRecordView) -> CheckResult:
    """The document's patient is this patient. A date of birth the document names must be the
    record's; a document that names none is read by a human before anything is confirmed."""
    proposed = batch.patient_date_of_birth
    if proposed is None:
        return _fail(PATIENT_MATCH, "patient_dob_not_proposed")
    if record.date_of_birth is not None and proposed != record.date_of_birth:
        return _fail(PATIENT_MATCH, "patient_mismatch")
    return _ok(PATIENT_MATCH)


def check_page(value: ProposedValue, pages: PageTexts) -> CheckResult:
    if value.page < 1 or value.page > pages.page_count:
        return _fail(PAGE_CITED, "page_out_of_range", page=value.page, page_count=pages.page_count)
    return _ok(PAGE_CITED, page=value.page)


def check_on_page(value: ProposedValue, pages: PageTexts) -> CheckResult:
    """Everything the model proposed stands, as written, on the page it cites. A value that
    is not on the page was not read from it — whatever else the checks say."""
    if value.page < 1 or value.page > pages.page_count:
        return _skip(ON_PAGE, "page_out_of_range")
    text = pages.text(value.page)
    if not text.strip():
        return _fail(ON_PAGE, "no_page_text", page=value.page)
    if not text_on_page(value.analyte_text, text):
        return _fail(ON_PAGE, "analyte_not_on_page", page=value.page)
    if not value_on_page(value.value_text, text):
        return _fail(ON_PAGE, "value_not_on_page", page=value.page)
    if value.unit_text and not text_on_page(value.unit_text, text):
        return _fail(ON_PAGE, "unit_not_on_page", page=value.page)
    if pages.source(value.page) == "ocr":
        # Found — on text an OCR engine produced. A misreading there looks like a reading.
        return _fail(ON_PAGE, "page_text_from_ocr", page=value.page)
    return _ok(ON_PAGE, page=value.page)


def check_mapping(
    value: ProposedValue, terminology: Terminology
) -> tuple[CheckResult, CatalogTerm | None]:
    term = terminology.resolve(value.analyte_text)
    if term is None:
        return _fail(MAPPING, "unmapped_analyte"), None
    return _ok(MAPPING, kpi_code=term.kpi_code), term


def check_value(value: ProposedValue) -> tuple[CheckResult, Decimal | None]:
    """The value is one plain number, readable one way only (imports/normalize rules)."""
    text = value.value_text.strip()
    if not normalize_mod.is_one_number(text):
        return _fail(VALUE, "value_not_a_number"), None
    return _ok(VALUE), Decimal(text.replace(",", "."))


def check_unit(
    value: ProposedValue, term: CatalogTerm | None, number: Decimal | None
) -> tuple[CheckResult, str | None, Decimal | None, Decimal | None]:
    """The unit is the KPI's canonical unit or converts to it by an APPROVED factor; the
    value is then held in the canonical unit. Returns (result, canonical unit, factor,
    normalized value). An unknown unit converts nothing."""
    if term is None or term.canonical_unit is None:
        return _skip(UNIT, "no_kpi"), None, None, None
    source = normalize_mod.canonical_unit_spelling(value.unit_text)
    if not source:
        return _fail(UNIT, "unit_missing"), None, None, None
    target = term.canonical_unit
    if source == target:
        return _ok(UNIT, canonical_unit=target), target, Decimal(1), number
    factor = normalize_mod.approved_factor(term.kpi_code, source, target)
    if factor is None:
        return _fail(UNIT, "unit_unknown", canonical_unit=target), None, None, None
    normalized = number * factor if number is not None else None
    return (
        _ok(UNIT, canonical_unit=target, factor=plain(factor)),
        target,
        factor,
        normalized,
    )


def check_reference(
    value: ProposedValue, factor: Decimal | None
) -> tuple[CheckResult, Decimal | None, Decimal | None]:
    """The reference bounds the laboratory wrote are carried as numbers in the unit the value
    is held in — both or neither (imports/normalize `_interval`). Never compared."""
    bounds: list[Decimal | None] = []
    readable = True
    for raw in (value.reference_low, value.reference_high):
        if raw is None or not raw.strip():
            bounds.append(None)
            continue
        if not normalize_mod.is_one_number(raw):
            readable = False
            bounds.append(None)
            continue
        bounds.append(Decimal(raw.strip().replace(",", ".")))
    low, high = bounds
    if readable and low is not None and high is not None and low > high:
        readable = False
    if not readable:
        return _fail(REFERENCE, "reference_unreadable"), None, None
    if low is None and high is None:
        return _ok(REFERENCE, given=False), None, None
    if factor is None:
        # No canonical unit to hold them in: the bounds stay what the source wrote.
        return _ok(REFERENCE, given=True, converted=False), low, high
    return (
        _ok(REFERENCE, given=True, converted=factor != 1),
        low * factor if low is not None else None,
        high * factor if high is not None else None,
    )


def check_plausibility(
    term: CatalogTerm | None,
    canonical_unit: str | None,
    normalized: Decimal | None,
    bounds: Bounds,
) -> tuple[CheckResult, PlausibilityBound | None]:
    if term is None or canonical_unit is None or normalized is None:
        return _skip(PLAUSIBILITY, "no_normalized_value"), None
    bound = bounds.for_kpi(term.kpi_code)
    if bound is None or bound.unit != canonical_unit:
        return _fail(PLAUSIBILITY, "plausibility_not_configured", kpi_code=term.kpi_code), None
    if (bound.hard_low is not None and normalized < bound.hard_low) or (
        bound.hard_high is not None and normalized > bound.hard_high
    ):
        return (
            _fail(
                PLAUSIBILITY,
                "outside_hard_bounds",
                hard_low=plain(bound.hard_low) if bound.hard_low is not None else None,
                hard_high=plain(bound.hard_high) if bound.hard_high is not None else None,
                unit=bound.unit,
            ),
            bound,
        )
    return _ok(PLAUSIBILITY), bound


def check_delta(
    term: CatalogTerm | None,
    canonical_unit: str | None,
    normalized: Decimal | None,
    bound: PlausibilityBound | None,
    record: PatientRecordView,
) -> CheckResult:
    """The change against the last published value of the same KPI, in the same unit, is not
    beyond the signed threshold. Context for a human, not a judgement of the patient."""
    if term is None or canonical_unit is None or normalized is None:
        return _skip(DELTA, "no_normalized_value")
    prior = record.last_published(term.kpi_code)
    if prior is None:
        return _ok(DELTA, prior=False)
    if prior.unit != canonical_unit:
        return _skip(DELTA, "prior_in_other_unit")
    if bound is None or bound.delta_max_relative is None:
        return _skip(DELTA, "delta_not_configured")
    if prior.value == 0:
        return _skip(DELTA, "prior_is_zero")
    relative = abs(normalized - prior.value) / abs(prior.value)
    detail = {
        "last_value": plain(prior.value),
        "relative_change": plain(relative.quantize(Decimal("0.001"))),
    }
    if relative > bound.delta_max_relative:
        return _fail(DELTA, "implausible_delta", **detail)
    return _ok(DELTA, prior=True, **detail)


def check_date(
    value: ProposedValue, batch: ProposedBatch, record: PatientRecordView, today: date
) -> CheckResult:
    day = _day(value)
    if day is None:
        return _fail(DATE, "date_missing")
    if record.date_of_birth is not None and day < record.date_of_birth:
        return _fail(DATE, "date_before_birth")
    if day > today:
        return _fail(DATE, "date_in_future", day=day.isoformat())
    if batch.issue_date is not None:
        if day > batch.issue_date:
            return _fail(
                DATE, "date_after_issue", day=day.isoformat(), issue=batch.issue_date.isoformat()
            )
        if day < batch.issue_date - ISSUE_WINDOW:
            return _fail(
                DATE, "date_outside_window", day=day.isoformat(), issue=batch.issue_date.isoformat()
            )
    return _ok(DATE, day=day.isoformat())


def _duplicate_key(value: ProposedValue, kpi_code: str | None) -> tuple[str, str | None, str, str]:
    day = _day(value)
    return (
        kpi_code or analyte_key(value.analyte_text),
        day.isoformat() if day is not None else None,
        _squash(value.value_text),
        normalize_mod.canonical_unit_spelling(value.unit_text) or "",
    )


def _measurement_key(value: ProposedValue, kpi_code: str | None) -> tuple[str, str | None]:
    day = _day(value)
    return (kpi_code or analyte_key(value.analyte_text), day.isoformat() if day else None)


def conflicting_measurements(
    batch: ProposedBatch, kpi_codes: list[str | None]
) -> set[tuple[str, str | None]]:
    """The (analyte, day) pairs this batch proposes with MORE THAN ONE distinct value or unit:
    the model read two numbers for one measurement, and neither can be confirmed unseen."""
    seen: dict[tuple[str, str | None], set[tuple[str, str]]] = {}
    for value, kpi_code in zip(batch.values, kpi_codes, strict=True):
        key = _measurement_key(value, kpi_code)
        seen.setdefault(key, set()).add(_duplicate_key(value, kpi_code)[2:])
    return {key for key, variants in seen.items() if len(variants) > 1}


def check_duplicate(
    value: ProposedValue,
    kpi_code: str | None,
    record: PatientRecordView,
    seen: set[tuple[str, str | None, str, str]],
    conflicts: set[tuple[str, str | None]] = frozenset(),  # type: ignore[assignment]
) -> CheckResult:
    """The same value is not already published for this patient (same KPI or name, same day,
    same text and unit), not proposed twice in this batch, and not one of two different
    readings of one measurement in this batch."""
    key = _duplicate_key(value, kpi_code)
    if key in seen:
        return _fail(DUPLICATE, "duplicate_in_batch")
    seen.add(key)
    if _measurement_key(value, kpi_code) in conflicts:
        return _fail(DUPLICATE, "conflicting_in_batch")
    if record.is_published(
        kpi_code=kpi_code,
        analyte_key=analyte_key(value.analyte_text),
        day=_day(value),
        value_text=_squash(value.value_text),
        unit_text=normalize_mod.canonical_unit_spelling(value.unit_text),
    ):
        return _fail(DUPLICATE, "duplicate_of_published")
    return _ok(DUPLICATE)


def check_confidence(value: ProposedValue) -> CheckResult:
    if value.confidence < GREEN_CONFIDENCE:
        return _fail(CONFIDENCE, "low_confidence", confidence=plain(value.confidence))
    return _ok(CONFIDENCE, confidence=plain(value.confidence))


# --- The run ---------------------------------------------------------------------------------


def run_checks(
    batch: ProposedBatch,
    *,
    terminology: Terminology,
    bounds: Bounds,
    record: PatientRecordView,
    pages: PageTexts,
    today: date,
) -> CheckedBatch:
    """Every check over every value, in a fixed order, with a fixed outcome per input."""
    patient = check_patient(batch, record)
    seen: set[tuple[str, str | None, str, str]] = set()
    conflicts = conflicting_measurements(
        batch,
        [
            term.kpi_code if (term := terminology.resolve(v.analyte_text)) is not None else None
            for v in batch.values
        ],
    )
    values: list[CheckedValue] = []
    for value in batch.values:
        page = check_page(value, pages)
        on_page = check_on_page(value, pages)
        mapping, term = check_mapping(value, terminology)
        value_result, number = check_value(value)
        unit, canonical_unit, factor, normalized = check_unit(value, term, number)
        reference, ref_low, ref_high = check_reference(value, factor)
        plausibility, bound = check_plausibility(term, canonical_unit, normalized, bounds)
        delta = check_delta(term, canonical_unit, normalized, bound, record)
        when = check_date(value, batch, record, today)
        duplicate = check_duplicate(value, term.kpi_code if term else None, record, seen, conflicts)
        confidence = check_confidence(value)
        checks = (
            patient,
            page,
            on_page,
            mapping,
            value_result,
            unit,
            reference,
            plausibility,
            delta,
            when,
            duplicate,
            confidence,
        )
        values.append(
            CheckedValue(
                proposal=value,
                kpi_code=term.kpi_code if term is not None else None,
                canonical_unit=canonical_unit,
                numeric_value=number,
                normalized_value=normalized,
                normalized_reference_low=ref_low,
                normalized_reference_high=ref_high,
                checks=checks,
                status=status_of(checks),
            )
        )
    return CheckedBatch(checks=(patient,), values=tuple(values))
